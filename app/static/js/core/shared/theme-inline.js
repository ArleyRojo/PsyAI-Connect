(function () {
  if (!document.documentElement.classList.contains('dark-mode')) {
    try {
      const cookieTheme = document.cookie
        .split('; ')
        .find(r => r.startsWith('theme='))
        ?.split('=')[1];
      const theme = cookieTheme || localStorage.getItem('theme');
      if (theme === 'dark') {
        document.documentElement.classList.add('dark-mode');
      }
    } catch (e) {}
  }
})();
