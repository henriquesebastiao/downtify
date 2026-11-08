---
icon: lucide/hard-drive
---

# Configurações do servidor

**Configurações → Servidor** reúne o funcionamento do próprio servidor. Só os administradores a veem (veja [Usuários e login](users.md#admins-and-users)).

## Mudando a porta

O Downtify escuta na porta **8000**. Um administrador pode escolher outra em **Configurações → Servidor → Porta** (1024–65535):

- **Salvar** guarda a escolha para a próxima vez que o servidor iniciar.
- **Salvar e reiniciar** reinicia o servidor nela na hora. Os downloads em andamento são interrompidos, e as páginas e os apps se reconectam. Uma página aberta no endereço do próprio servidor (por exemplo, `http://nas:8000`) espera o servidor voltar e abre o novo endereço sozinha; você continua conectado.

Quando a porta vem da variável de ambiente `DOWNTIFY_PORT` (ou `PORT`) ou de `--port` na linha de comando — que sempre prevalecem —, o campo mostra a porta em uso, mas não pode ser editado, e a página diz qual delas a define. Remova-a (e reinicie) para escolher a porta nas Configurações.

::: warning A rede bridge do Docker mapeia uma porta fixa
Na instalação padrão do Docker (`ports: - '8000:8000'`), a porta do contêiner precisa coincidir com o mapeamento. Depois de mudá-la nas Configurações, altere o mapeamento para a nova porta (`'9000:9000'`) e recrie o contêiner — ou execute com `network_mode: host`. Caso contrário, o Downtify fica inacessível. Para voltar a entrar, defina `DOWNTIFY_PORT` com a porta antiga: ela prevalece sobre as Configurações.
:::

Atrás de um [proxy reverso](mobile-apps.md#behind-a-reverse-proxy), aponte o proxy também para a nova porta. Os [apps pareados](mobile-apps.md) usam o endereço que receberam: depois de trocar a porta, informe o novo endereço no app.
