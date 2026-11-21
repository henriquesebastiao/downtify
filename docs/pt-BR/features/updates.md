---
icon: lucide/download
---

# Avisos de atualização

O Downtify consulta a própria [página de Releases no GitHub](https://github.com/henriquesebastiao/downtify/releases) uma vez por hora. Quando há uma versão mais nova, um aviso aparece no fim da barra lateral em todas as páginas — no celular, um ponto na aba **Mais** e uma linha no topo da sua folha — e em **Configurações → Sobre**:

> ✦ Atualização 3.0.1 disponível

Clique nele para abrir essa versão no GitHub.

## Novidades após uma atualização

Na primeira vez que o app web abre depois que o Downtify foi atualizado, uma janela **Novidades do Downtify 3.12.0** lista os destaques da versão, com um botão **Changelog completo** que abre a versão no GitHub e uma linha discreta para dar uma estrela ao repositório. **Entendi** (ou fechar a janela) a esconde até a próxima atualização. **Configurações → Sobre → Novidades** a abre de novo.

- Fica guardado por navegador: cada navegador (e cada pessoa conectada nele) a vê uma vez por atualização. Um navegador que nunca abriu o Downtify — uma instalação nova — não a vê.
- Os destaques vêm junto com o app, então a janela funciona sem internet; só os dois links vão para o GitHub. Uma versão sem destaques escritos mostra apenas o link para o changelog.
- Ela espera o login e não abre por cima do aviso para trocar a senha padrão.

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
