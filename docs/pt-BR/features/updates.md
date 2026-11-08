---
icon: lucide/download
---

# Avisos de atualização

O Downtify consulta a própria [página de Releases no GitHub](https://github.com/henriquesebastiao/downtify/releases) uma vez por hora. Quando há uma versão mais nova, um aviso aparece no fim da barra lateral em todas as páginas — no celular, um ponto na aba **Mais** e uma linha no topo da sua folha — e em **Configurações → Sobre**:

> ✦ Atualização 3.0.1 disponível

Clique nele para abrir essa versão no GitHub.

## Como funciona

- Uma tarefa em segundo plano no backend (`downtify/update_check.py`) busca a versão mais recente na API do GitHub uma vez logo na inicialização e depois a cada hora. É do tipo "dispara e esquece": nada na interface espera por ela.
- A interface web lê o resultado em cache de `GET /api/check_update` (veja a [Referência da API](../api-reference.md)) uma vez por hora e mostra o aviso quando encontra uma versão mais nova.
- As versões são comparadas numericamente (`2.10.0` < `2.9.0` é falso, ao contrário de uma comparação simples de texto), e um prefixo `v` opcional na tag da release é ignorado.

## Se o GitHub estiver inacessível

Uma verificação que falha (host offline, limite de requisições do GitHub) é registrada no log e simplesmente repetida na próxima passagem horária — o resultado anterior, se houver, continua valendo até lá. A verificação nunca bloqueia nada do que o Downtify faz; não há erro visível para o usuário.

## Nada é baixado automaticamente

Isso apenas *avisa* que existe uma nova versão — o Downtify não se atualiza sozinho. Para atualizar de fato, baixe a nova imagem e recrie o contêiner:

```bash
docker compose pull
docker compose up -d
```
