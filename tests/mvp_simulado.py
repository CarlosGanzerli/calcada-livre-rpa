"""MVP simulado em memória, com o mesmo contrato da API real (calcada-livre/mvp).

Usado quando o código do MVP não está ao lado deste repositório. Se estiver
(pasta ../calcada-livre/mvp ou variável MVP_DIR), os testes usam o MVP real.
"""
import json
import uuid
from datetime import datetime, timezone

import httpx

CHAVE = "chave-de-teste"
ORIGENS = {"app", "carrinho", "visao"}
CAMPOS_PATCH = {"status", "prioridade", "protocolo", "subprefeitura", "motivo", "duplicada_de", "descricao"}


def criar_cliente() -> httpx.Client:
    banco: dict[str, dict] = {}

    def responder(req: httpx.Request) -> httpx.Response:
        caminho = req.url.path
        if caminho == "/api/ocorrencias" and req.method == "POST":
            d = json.loads(req.content)
            if d.get("origem") not in ORIGENS or not {"tipo", "latitude", "longitude"} <= d.keys():
                return httpx.Response(422, json={"detail": "inválido"})
            agora = datetime.now(timezone.utc).isoformat()
            oc = {"id": str(uuid.uuid4()), "descricao": None, "foto_url": None, "confianca": None, **d,
                  "criada_em": agora, "atualizada_em": agora, "status": "nova", "prioridade": None,
                  "protocolo": None, "subprefeitura": None, "motivo": None, "duplicada_de": None}
            banco[oc["id"]] = oc
            return httpx.Response(201, json=oc)
        if caminho == "/api/ocorrencias" and req.method == "GET":
            itens = sorted(banco.values(), key=lambda o: o["criada_em"], reverse=True)
            if s := req.url.params.get("status"):
                itens = [o for o in itens if o["status"] == s]
            if desde := req.url.params.get("desde"):
                itens = [o for o in itens if o["criada_em"] >= desde]
            return httpx.Response(200, json=itens)
        if caminho.startswith("/api/ocorrencias/"):
            oc = banco.get(caminho.rsplit("/", 1)[1])
            if req.method == "PATCH" and req.headers.get("X-API-Key") != CHAVE:
                return httpx.Response(401)
            if not oc:
                return httpx.Response(404)
            if req.method == "PATCH":
                oc.update({k: v for k, v in json.loads(req.content).items() if k in CAMPOS_PATCH})
            return httpx.Response(200, json=oc)
        return httpx.Response(404)

    return httpx.Client(base_url="http://testserver", transport=httpx.MockTransport(responder))
