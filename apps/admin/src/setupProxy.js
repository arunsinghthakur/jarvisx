const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  const adminTarget =
    process.env.REACT_APP_ADMIN_API_BASE ||
    process.env.REACT_APP_API_BASE ||
    'http://localhost:5002'

  const proxyOptions = {
    target: adminTarget,
    changeOrigin: true,
    cookieDomainRewrite: '',
    cookiePathRewrite: {
      '/api/auth': '/api/auth',
      '/api': '/api',
    },
    onProxyRes: function(proxyRes) {
      if (proxyRes.headers['set-cookie']) {
        proxyRes.headers['set-cookie'] = proxyRes.headers['set-cookie'].map(cookie => {
          return cookie
            .replace(/;\s*secure/gi, '')
            .replace(/;\s*samesite=strict/gi, '; samesite=lax')
            .replace(/;\s*samesite=none/gi, '; samesite=lax');
        });
      }
    },
  }

  app.use('/api', createProxyMiddleware(proxyOptions));
  app.use('/health', createProxyMiddleware(proxyOptions));
};
