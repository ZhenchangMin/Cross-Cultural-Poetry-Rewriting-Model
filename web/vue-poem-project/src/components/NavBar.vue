<template>
  <nav class="navbar">
    <router-link to="/" class="nav-brand" aria-label="Poem Bridge Home">
      <span class="brand-mark">詩</span>
      <div class="brand-text-wrap">
        <span class="brand-zh">诗渡</span>
        <span class="brand-en">Poem&nbsp;Bridge</span>
      </div>
    </router-link>

    <ul class="nav-links">
      <li v-for="item in navItems" :key="item.key">
        <router-link
          v-if="item.to"
          :to="item.to"
          class="nav-link"
          active-class="active"
        >
          <span class="nav-link-zh">{{ item.zh }}</span>
          <span class="nav-link-en">{{ item.en }}</span>
        </router-link>
        <button
          v-else
          type="button"
          class="nav-link nav-link--soon"
          disabled
          :title="'即将上线 / Coming soon'"
        >
          <span class="nav-link-zh">{{ item.zh }}</span>
          <span class="nav-link-en">{{ item.en }}</span>
        </button>
      </li>
    </ul>
  </nav>
</template>

<script setup>
const navItems = [
  { key: 'about',       zh: '关于我们', en: 'About',      to: '/about' },
  { key: 'changelog',   zh: '更新日志', en: 'Changelog',  to: '/changelog' },
  { key: 'disclaimer',  zh: '免责声明', en: 'Disclaimer', to: '/disclaimer' }
]
</script>

<style scoped>
.navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 4px 14px;
  position: relative;
  z-index: 2;
  border-bottom: 1px solid var(--border);
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  user-select: none;
  text-decoration: none;
  color: inherit;
  transition: opacity 0.2s ease;
}
.nav-brand:hover { opacity: 0.85; }

.brand-mark {
  font-family: 'Noto Serif SC', serif;
  font-size: 30px;
  font-weight: 600;
  color: var(--red);
  line-height: 1;
  width: 46px;
  height: 46px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--red-border);
  border-radius: 4px;
  background: var(--red-ghost);
  box-shadow: 0 0 0 4px rgba(192, 56, 40, 0.04);
}

.brand-text-wrap {
  display: flex;
  flex-direction: column;
  gap: 2px;
  line-height: 1.1;
}

.brand-zh {
  font-family: 'Noto Serif SC', serif;
  font-size: 20px;
  font-weight: 500;
  letter-spacing: 0.22em;
  color: var(--text-parchment);
}

.brand-en {
  font-family: 'Cinzel', serif;
  font-size: 11px;
  letter-spacing: 0.32em;
  color: var(--text-faded);
  text-transform: uppercase;
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 4px;
  list-style: none;
  margin: 0;
  padding: 0;
}

.nav-link {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 8px 18px;
  background: transparent;
  border: none;
  cursor: pointer;
  font-family: inherit;
  color: var(--text-aged);
  text-decoration: none;
  transition: color 0.25s ease;
}

.nav-link-zh {
  font-family: 'Noto Serif SC', serif;
  font-size: 14px;
  letter-spacing: 0.18em;
  line-height: 1.1;
}

.nav-link-en {
  font-family: 'Cinzel', serif;
  font-size: 9px;
  letter-spacing: 0.28em;
  color: var(--text-faded);
  text-transform: uppercase;
  transition: color 0.25s ease;
}

.nav-link::after {
  content: '';
  position: absolute;
  left: 50%;
  bottom: 0;
  width: 0;
  height: 1px;
  background: var(--red);
  transform: translateX(-50%);
  transition: width 0.3s ease;
}

.nav-link:not(:disabled):hover {
  color: var(--red);
}
.nav-link:not(:disabled):hover .nav-link-en {
  color: var(--red);
  opacity: 0.7;
}
.nav-link:not(:disabled):hover::after {
  width: 60%;
}

.nav-link.active {
  color: var(--red);
}
.nav-link.active .nav-link-en {
  color: var(--red);
  opacity: 0.7;
}
.nav-link.active::after {
  width: 60%;
}

.nav-link--soon {
  opacity: 0.4;
  cursor: not-allowed;
}
.nav-link--soon:hover { color: var(--text-aged); }

/* ── Responsive (mobile) ── */
@media (max-width: 820px) {
  .navbar {
    padding: 10px 0 8px;
    gap: 8px;
  }

  .nav-brand { gap: 8px; }

  .brand-mark {
    width: 36px;
    height: 36px;
    font-size: 22px;
    box-shadow: 0 0 0 2px rgba(192, 56, 40, 0.04);
  }

  .brand-zh {
    font-size: 15px;
    letter-spacing: 0.16em;
  }
  .brand-en {
    font-size: 9px;
    letter-spacing: 0.24em;
  }

  .nav-links { gap: 0; }

  .nav-link {
    padding: 6px 8px;
    gap: 1px;
  }
  .nav-link-zh {
    font-size: 11px;
    letter-spacing: 0.12em;
  }
  .nav-link-en {
    font-size: 7px;
    letter-spacing: 0.2em;
  }
}

@media (max-width: 420px) {
  /* 极窄屏：隐藏英文行，只保留中文，避免溢出 */
  .brand-en { display: none; }
  .nav-link-en { display: none; }
  .brand-zh { font-size: 14px; }
}
</style>
