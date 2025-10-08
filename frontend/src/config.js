const config = {
  PROTOCOL: process.env.PROTOCOL || window.location.protocol,
  WS_PROTOCOL:
    process.env.WS_PROTOCOL || window.location.protocol === 'https:'
      ? 'wss:'
      : 'ws:',
  BACKEND: process.env.BACKEND || window.location.hostname,
  PORT: process.env.PORT || window.location.port,
  WS_PORT: process.env.WS_PORT || window.location.port,
  BASEURL: process.env.BASEURL || '',
}

export default config
