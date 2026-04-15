"""Coinbase Developer Platform wallet provider for x402 agent wallets.

Creates and retrieves EVM accounts on Base (Sepolia/Mainnet) via CDP SDK.
LAP stores only the wallet address — never private keys.
"""

import logging

from app.config import settings

logger = logging.getLogger(__name__)


class WalletProviderError(Exception):
    pass


def _cdp_configured() -> bool:
    return bool(
        settings.cdp_api_key_id
        and settings.cdp_api_key_secret
        and settings.cdp_wallet_secret
    )


async def create_wallet() -> str:
    """Create a new EVM account via CDP and return its address.

    Returns the hex address (e.g. "0x1234...").
    Raises WalletProviderError if CDP is not configured or creation fails.
    """
    if not _cdp_configured():
        raise WalletProviderError(
            "CDP credentials not configured. "
            "Set CDP_API_KEY_ID, CDP_API_KEY_SECRET, CDP_WALLET_SECRET in .env"
        )

    try:
        from cdp import CdpClient

        async with CdpClient(
            api_key_id=settings.cdp_api_key_id,
            api_key_secret=settings.cdp_api_key_secret,
            wallet_secret=settings.cdp_wallet_secret,
        ) as cdp:
            account = await cdp.evm.create_account()
            logger.info("Created CDP wallet: %s", account.address)
            return account.address
    except ImportError:
        raise WalletProviderError("cdp-sdk is not installed. Run: pip install cdp-sdk")
    except Exception as e:
        logger.error("Failed to create CDP wallet: %s", e, exc_info=True)
        raise WalletProviderError(f"CDP wallet creation failed: {e}")


async def get_wallet_balance(address: str, asset: str = "usdc") -> dict:
    """Get wallet balance for a given asset. Returns {"balance": "0.00", "asset": "USDC"}.

    This is a read-only operation — no keys needed, just the address.
    """
    if not _cdp_configured():
        raise WalletProviderError("CDP credentials not configured")

    try:
        from cdp import CdpClient

        async with CdpClient(
            api_key_id=settings.cdp_api_key_id,
            api_key_secret=settings.cdp_api_key_secret,
            wallet_secret=settings.cdp_wallet_secret,
        ) as cdp:
            balance = await cdp.evm.get_balance(address=address, asset=asset)
            return {"balance": str(balance), "asset": asset.upper()}
    except ImportError:
        raise WalletProviderError("cdp-sdk is not installed")
    except Exception as e:
        logger.error("Failed to get balance for %s: %s", address, e)
        raise WalletProviderError(f"Balance check failed: {e}")
