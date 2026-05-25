"""Open Targets Platform — public GraphQL API (no auth). Spec §2.5 F9.

Open Targets aggregates target-disease evidence across genetics
(ClinVar / UK Biobank / gnomAD constraint), drugs (ChEMBL),
text-mined literature (EuropePMC), pathways (Reactome), expression
(Expression Atlas), and animal models. The platform exposes a public
GraphQL endpoint at:

    https://api.platform.opentargets.org/api/v4/graphql

No API key. Fair-use rate limit only.

Patient #2 E2 in the v1.3.0 EVAL panel asked for "tractable secondary
targets" downstream of an established primary biomarker — this is the
canonical Open Targets question.

Key formats:
  * ``target:<ensembl_id_or_symbol>``      — target-level evidence summary
  * ``disease:<EFO_id>``                   — disease-level associated targets
  * ``target_disease:<symbol>:<EFO_id>``   — joint association score + evidence count

TTL: 7 days (Open Targets release cadence is quarterly).
"""
from __future__ import annotations

from typing import Any

import httpx

from .base import Integrator, IntegratorError


_ENDPOINT = "https://api.platform.opentargets.org/api/v4/graphql"


_QUERY_TARGET = """
query targetEvidence($id: String!) {
  target(ensemblId: $id) {
    id
    approvedSymbol
    approvedName
    biotype
    associatedDiseases(page: {index: 0, size: 25}) {
      count
      rows { score disease { id name } }
    }
    knownDrugs(size: 25) {
      count
      rows { drug { id name } mechanismOfAction phase status }
    }
  }
}
""".strip()

_QUERY_DISEASE = """
query diseaseAssociations($id: String!) {
  disease(efoId: $id) {
    id
    name
    associatedTargets(page: {index: 0, size: 25}) {
      count
      rows { score target { id approvedSymbol approvedName } }
    }
  }
}
""".strip()

_QUERY_TARGET_DISEASE = """
query targetDiseaseAssoc($efo: String!, $sym: String!) {
  target(approvedSymbol: $sym) {
    id
    approvedSymbol
    associatedDiseases(page: {index: 0, size: 5}, BFilter: {Bs: [$efo]}) {
      count
      rows { score disease { id name } datasourceScores { id score } }
    }
  }
}
""".strip()


class OpenTargetsIntegrator(Integrator):
    family = "F9"
    ttl_seconds = 7 * 24 * 3600

    async def fetch(self, key: str) -> dict[str, Any]:
        if key.startswith("target:"):
            return await self._query_target(key[len("target:"):].strip())
        if key.startswith("disease:"):
            return await self._query_disease(key[len("disease:"):].strip())
        if key.startswith("target_disease:"):
            rest = key[len("target_disease:"):].strip()
            if ":" not in rest:
                raise IntegratorError(
                    f"Open Targets: target_disease:<symbol>:<EFO> required, got {key!r}"
                )
            sym, efo = rest.split(":", 1)
            return await self._query_target_disease(sym.strip(), efo.strip())
        raise IntegratorError(
            f"Open Targets: unrecognised key prefix {key!r} — "
            "expected target:<id>, disease:<EFO>, or target_disease:<symbol>:<EFO>"
        )

    async def _post(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=30.0) as http:
                r = await http.post(
                    _ENDPOINT,
                    json={"query": query, "variables": variables},
                    headers={"Content-Type": "application/json"},
                )
        except (httpx.HTTPError, ConnectionError, OSError) as e:
            raise IntegratorError(f"Open Targets transport: {e}") from e
        if r.status_code >= 400:
            raise IntegratorError(f"Open Targets HTTP {r.status_code}: {r.text}")
        body = r.json()
        if body.get("errors"):
            raise IntegratorError(f"Open Targets GraphQL errors: {body['errors']}")
        data = body.get("data") or {}
        if not data:
            raise IntegratorError("Open Targets: empty data block")
        return data

    async def _query_target(self, ident: str) -> dict[str, Any]:
        data = await self._post(_QUERY_TARGET, {"id": ident})
        t = data.get("target") or {}
        if not t:
            raise IntegratorError(f"Open Targets: target {ident!r} not found")
        diseases = (t.get("associatedDiseases") or {}).get("rows") or []
        drugs = (t.get("knownDrugs") or {}).get("rows") or []
        return {
            "target_id": t.get("id"),
            "symbol": t.get("approvedSymbol"),
            "name": t.get("approvedName"),
            "biotype": t.get("biotype"),
            "associated_diseases": [
                {"efo": (d.get("disease") or {}).get("id"),
                 "name": (d.get("disease") or {}).get("name"),
                 "score": d.get("score")}
                for d in diseases
            ],
            "known_drugs": [
                {"drug_id": (d.get("drug") or {}).get("id"),
                 "name": (d.get("drug") or {}).get("name"),
                 "mechanism": d.get("mechanismOfAction"),
                 "phase": d.get("phase"),
                 "status": d.get("status")}
                for d in drugs
            ],
        }

    async def _query_disease(self, efo: str) -> dict[str, Any]:
        data = await self._post(_QUERY_DISEASE, {"id": efo})
        d = data.get("disease") or {}
        if not d:
            raise IntegratorError(f"Open Targets: disease {efo!r} not found")
        targets = (d.get("associatedTargets") or {}).get("rows") or []
        return {
            "efo": d.get("id"),
            "name": d.get("name"),
            "associated_targets": [
                {"symbol": (t.get("target") or {}).get("approvedSymbol"),
                 "name": (t.get("target") or {}).get("approvedName"),
                 "ensembl": (t.get("target") or {}).get("id"),
                 "score": t.get("score")}
                for t in targets
            ],
        }

    async def _query_target_disease(self, sym: str, efo: str) -> dict[str, Any]:
        data = await self._post(_QUERY_TARGET_DISEASE, {"efo": efo, "sym": sym})
        t = data.get("target") or {}
        if not t:
            raise IntegratorError(
                f"Open Targets: target {sym!r} not found for disease {efo!r}"
            )
        rows = (t.get("associatedDiseases") or {}).get("rows") or []
        return {
            "symbol": t.get("approvedSymbol"),
            "ensembl": t.get("id"),
            "efo": efo,
            "associations": [
                {"score": r.get("score"),
                 "disease": (r.get("disease") or {}).get("name"),
                 "datasource_scores": r.get("datasourceScores") or []}
                for r in rows
            ],
        }
