"""Subscription and billing API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import stripe
from ..database import get_db
from ..models import User, SubscriptionTier
from ..services.quota_service import QuotaService
from ..api.auth import get_current_user_from_token
from ..config import settings

# Initialize Stripe
stripe.api_key = settings.stripe_secret_key

router = APIRouter(prefix="/api/v1/subscriptions", tags=["subscriptions"])


class CreateCheckoutSessionRequest(BaseModel):
    """Request to create a Stripe checkout session."""
    price_id: str
    success_url: str
    cancel_url: str


class CreatePortalSessionRequest(BaseModel):
    """Request to create a Stripe portal session."""
    return_url: str


@router.post("/create-checkout-session")
async def create_checkout_session(
    request: CreateCheckoutSessionRequest,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    """
    Create a Stripe Checkout session for subscription purchase.
    """
    try:
        # Create or get Stripe customer
        if not current_user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=current_user.email,
                metadata={"user_id": current_user.id}
            )
            current_user.stripe_customer_id = customer.id
            db.commit()
        
        # Create checkout session
        session = stripe.checkout.Session.create(
            customer=current_user.stripe_customer_id,
            payment_method_types=["card"],
            line_items=[{
                "price": request.price_id,
                "quantity": 1,
            }],
            mode="subscription",
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            metadata={"user_id": current_user.id}
        )
        
        return {"checkout_url": session.url, "session_id": session.id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create checkout session: {str(e)}")


@router.post("/create-portal-session")
async def create_portal_session(
    request: CreatePortalSessionRequest,
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Create a Stripe Customer Portal session for subscription management.
    """
    if not current_user.stripe_customer_id:
        raise HTTPException(
            status_code=400,
            detail="No active subscription found"
        )
    
    try:
        session = stripe.billing_portal.Session.create(
            customer=current_user.stripe_customer_id,
            return_url=request.return_url,
        )
        
        return {"portal_url": session.url}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create portal session: {str(e)}")


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle Stripe webhook events.
    
    This endpoint handles subscription lifecycle events:
    - checkout.session.completed: New subscription
    - customer.subscription.updated: Subscription changed
    - customer.subscription.deleted: Subscription cancelled
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Handle the event
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        await _handle_checkout_completed(session, db)
    
    elif event["type"] == "customer.subscription.updated":
        subscription = event["data"]["object"]
        await _handle_subscription_updated(subscription, db)
    
    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        await _handle_subscription_deleted(subscription, db)
    
    return {"status": "success"}


async def _handle_checkout_completed(session: dict, db: Session):
    """Handle successful checkout."""
    user_id = int(session["metadata"]["user_id"])
    subscription_id = session["subscription"]
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return
    
    # Get subscription details from Stripe
    subscription = stripe.Subscription.retrieve(subscription_id)
    price_id = subscription["items"]["data"][0]["price"]["id"]
    
    # Map price ID to tier
    tier = _get_tier_from_price_id(price_id)
    
    # Update user
    user.stripe_subscription_id = subscription_id
    user.subscription_tier = tier
    db.commit()
    
    # Update quota
    QuotaService.get_or_create_subscription(db, user)


async def _handle_subscription_updated(subscription: dict, db: Session):
    """Handle subscription update."""
    subscription_id = subscription["id"]
    
    user = db.query(User).filter(
        User.stripe_subscription_id == subscription_id
    ).first()
    
    if not user:
        return
    
    # Check subscription status
    if subscription["status"] == "active":
        price_id = subscription["items"]["data"][0]["price"]["id"]
        tier = _get_tier_from_price_id(price_id)
        user.subscription_tier = tier
    elif subscription["status"] in ["past_due", "unpaid", "canceled"]:
        user.subscription_tier = SubscriptionTier.FREE
    
    db.commit()
    
    # Update quota
    QuotaService.get_or_create_subscription(db, user)


async def _handle_subscription_deleted(subscription: dict, db: Session):
    """Handle subscription cancellation."""
    subscription_id = subscription["id"]
    
    user = db.query(User).filter(
        User.stripe_subscription_id == subscription_id
    ).first()
    
    if not user:
        return
    
    # Downgrade to free tier
    user.subscription_tier = SubscriptionTier.FREE
    user.stripe_subscription_id = None
    db.commit()
    
    # Update quota
    QuotaService.get_or_create_subscription(db, user)


def _get_tier_from_price_id(price_id: str) -> SubscriptionTier:
    """Map Stripe price ID to subscription tier."""
    # These would be your actual Stripe price IDs
    tier_mapping = {
        "price_pro_monthly": SubscriptionTier.PRO,
        "price_pro_yearly": SubscriptionTier.PRO,
        "price_enterprise_monthly": SubscriptionTier.ENTERPRISE,
        "price_enterprise_yearly": SubscriptionTier.ENTERPRISE,
    }
    
    return tier_mapping.get(price_id, SubscriptionTier.FREE)


@router.get("/prices")
async def get_prices():
    """Get available subscription prices."""
    return {
        "pro_monthly": {
            "price_id": "price_pro_monthly",
            "amount": 2900,  # $29.00
            "currency": "usd",
            "interval": "month"
        },
        "pro_yearly": {
            "price_id": "price_pro_yearly",
            "amount": 29000,  # $290.00 (2 months free)
            "currency": "usd",
            "interval": "year"
        },
        "enterprise_monthly": {
            "price_id": "price_enterprise_monthly",
            "amount": 9900,  # $99.00
            "currency": "usd",
            "interval": "month"
        },
        "enterprise_yearly": {
            "price_id": "price_enterprise_yearly",
            "amount": 99000,  # $990.00 (2 months free)
            "currency": "usd",
            "interval": "year"
        }
    }



