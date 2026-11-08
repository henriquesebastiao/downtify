---
title: Deemix
icon: lucide/music
---

# Fonte de áudio Deemix

O Deemix é uma fonte de áudio opcional, desativada por padrão. Configure-o em
**Configurações → Fontes de áudio**, abaixo do slskd, e ative-o na ordem das fontes.
Exige o seu próprio servidor Deemix compatível e uma conta Deezer com direito à
qualidade solicitada. Não fornece uma assinatura nem contorna uma.

## Credenciais e pastas compartilhadas

Mantenha o modo de login normal por sessão do Deemix. Não ative o modo de
usuário único em um servidor desprotegido: o endpoint de conexão dele devolve o ARL compartilhado.

Monte no Downtify um arquivo privado com o seu ARL do Deezer, legível apenas
pela conta de serviço, e defina `DOWNTIFY_DEEMIX_ARL_FILE` com esse caminho.
O ARL só é lido ao abrir uma sessão por cookie. Ele nunca é guardado nas
configurações, devolvido ao navegador nem registrado em log. Trate-o como uma senha;
obtenha-o e substitua-o em particular, não em issues ou chats. A integração
nunca altera o login nem as configurações de download do Deemix para todo o servidor.
O teste de conexão não coloca downloads na fila.

| Configuração                  | Finalidade                                                         |
| ----------------------------- | ------------------------------------------------------------------ |
| URL do servidor               | Endereço interno do Deemix, por exemplo `http://deemix:6595`       |
| Pasta de download dentro do Deemix | Normalmente `/downloads`                                      |
| Mesma pasta dentro do Downtify | Bind mount compartilhado, por exemplo `/deemix`; somente leitura é aceito |
| Qualidade                     | MP3 128, MP3 320 ou FLAC; direitos não compatíveis falham de forma explícita |

A pasta compartilhada é registrada como pasta de biblioteca externa ao salvar.
Os arquivos ficam lá, na organização de artista/álbum do Deemix. O Downtify preserva
o formato, as tags, a capa e os arquivos `.lrc` deles, sem regravá-los.
As letras embutidas e os `.lrc` de mesmo nome são lidos pelo player.
Nenhum áudio ou letra é apagado, movido ou gerado por esta integração.

Um link de faixa do Deezer seleciona aquela gravação. Downloads entre catálogos exigem
correspondência exata e inequívoca de artista/título, com álbum e duração coincidentes
quando informados. Uma correspondência ambígua passa para a próxima fonte ativada.
A conclusão da fila do Deemix é seguida de uma verificação de arquivo e de duração/qualidade.
A integração nunca limpa, cancela nem altera tarefas manuais do Deemix.
Links explícitos do YouTube mantêm o comportamento atual de download direto.

Esta fonte não substitui nem apaga automaticamente uma faixa existente da
biblioteca. A deduplicação da biblioteca e a substituição manual de áudio continuam separadas.
