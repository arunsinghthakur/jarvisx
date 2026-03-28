const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  const adminTarget =
    process.env.REACT_APP_ADMIN_API_BASE ||
    process.env.REACT_APP_API_BASE ||
    'http://localhost:5002'

  const speechTarget =
    process.env.REACT_APP_SPEECH_API_BASE ||
    'http://localhost:9003'

  const cookieHandler = function(proxyRes) {
    if (proxyRes.headers['set-cookie']) {
      proxyRes.headers['set-cookie'] = proxyRes.headers['set-cookie'].map(cookie => {
        return cookie
          .replace(/;\s*secure/gi, '')
          .replace(/;\s*samesite=strict/gi, '; samesite=lax')
          .replace(/;\s*samesite=none/gi, '; samesite=lax');
      });
    }
  };

  const adminProxyOptions = {
    target: adminTarget,
    changeOrigin: true,
    cookieDomainRewrite: '',
    onProxyRes: cookieHandler,
  };

  app.use('/api/auth', createProxyMiddleware(adminProxyOptions));
  app.use('/api/workspace-config', createProxyMiddleware(adminProxyOptions));
  app.use('/api/conversations', createProxyMiddleware(adminProxyOptions));
  app.use('/api/chatbot', createProxyMiddleware(adminProxyOptions));
  
  app.use(
    '/api',
    createProxyMiddleware({
      target: speechTarget,
      changeOrigin: true,
    })
  );
};
