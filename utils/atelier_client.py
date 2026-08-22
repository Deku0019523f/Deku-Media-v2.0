# -*- coding: utf-8 -*-
"""
Client pour l'API de paiement Atelier (Mobile Money / carte bancaire)
Doc : https://myateliers.store/docs/api
"""
import aiohttp
import json
from typing import Optional, Dict
from config import ATELIER_API_KEY, ATELIER_BASE_URL, ATELIER_CALLBACK_URL, ATELIER_RETURN_URL


class AtelierAPIError(Exception):
    """Levée quand l'API Atelier renvoie une erreur ou est injoignable"""
    def __init__(self, message: str, code: Optional[str] = None, http_status: Optional[int] = None):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


class AtelierClient:
    def __init__(self):
        self.base_url = ATELIER_BASE_URL
        self.api_key = ATELIER_API_KEY
        self.timeout = aiohttp.ClientTimeout(total=15)

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def create_payment(self, amount: int, description: str, customer_name: str,
                              customer_phone: Optional[str] = None,
                              metadata: Optional[dict] = None) -> Dict:
        """Crée un paiement et retourne le dict 'data' de la réponse (contient checkout_url, reference...)"""
        if not self.api_key:
            raise AtelierAPIError(
                "ATELIER_API_KEY n'est pas configurée (variable d'environnement manquante).",
                code="missing_api_key"
            )

        customer = {"name": customer_name}
        if customer_phone:
            customer["phone"] = customer_phone

        payload = {
            "amount": amount,
            "description": description,
            "customer": customer,
            "return_url": ATELIER_RETURN_URL,
            "callback_url": ATELIER_CALLBACK_URL,
            "metadata": metadata or {},
        }

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    f"{self.base_url}/payments", json=payload, headers=self._headers()
                ) as resp:
                    status = resp.status
                    raw_text = await resp.text()
        except aiohttp.ClientError as e:
            raise AtelierAPIError(f"Impossible de contacter l'API Atelier : {e}") from e

        try:
            data = json.loads(raw_text)
        except ValueError:
            raise AtelierAPIError(
                f"Réponse non-JSON de l'API Atelier (HTTP {status}) : {raw_text[:200]!r}",
                http_status=status
            )

        if status != 201 or not data.get("success"):
            detail = data.get("message") or data.get("error") or data.get("code", "unknown_error")
            raise AtelierAPIError(detail, code=data.get("code"), http_status=status)

        return data["data"]

    async def get_payment_status(self, reference: str) -> Dict:
        """Vérifie le statut réel d'un paiement auprès de l'API (source de vérité)"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(
                    f"{self.base_url}/payments/{reference}", headers=self._headers()
                ) as resp:
                    status = resp.status
                    raw_text = await resp.text()
        except aiohttp.ClientError as e:
            raise AtelierAPIError(f"Impossible de contacter l'API Atelier : {e}") from e

        try:
            data = json.loads(raw_text)
        except ValueError:
            raise AtelierAPIError(
                f"Réponse non-JSON de l'API Atelier (HTTP {status}) : {raw_text[:200]!r}",
                http_status=status
            )

        if status != 200 or not data.get("success"):
            detail = data.get("message") or data.get("error") or data.get("code", "unknown_error")
            raise AtelierAPIError(detail, code=data.get("code"), http_status=status)

        return data["data"]


# Instance globale
atelier_client = AtelierClient()
