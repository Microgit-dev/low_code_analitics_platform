<template>
  <main class="auth-layout">
    <section class="hero">
      <h1>Low Code Analytics</h1>
      <p>
        Базовый старт платформы: авторизация, личные workspace и подготовка к
        следующим контурам low-code.
      </p>
    </section>

    <section class="card">
      <slot />
    </section>
  </main>
</template>

<style scoped>
.auth-layout {
  min-height: 100vh;
  padding: 32px 20px;
  display: grid;
  grid-template-columns: 1.15fr 1fr;
  gap: 28px;
  align-items: center;
}

.hero {
  background:
    radial-gradient(circle at 84% 20%, rgba(255, 255, 255, 0.18) 0%, transparent 38%),
    linear-gradient(135deg, #2f5f78 0%, #2f6f80 45%, #2e8d78 100%);
  border-radius: 22px;
  padding: 42px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: 0 16px 30px rgba(31, 65, 72, 0.25);
  color: #eaf9fb;
}

.hero h1 {
  margin: 0;
  font-size: clamp(2rem, 6vw, 3.2rem);
  line-height: 1.05;
}

.hero p {
  margin-top: 16px;
  max-width: 480px;
  color: #c8e4ea;
}

.card {
  background: var(--bg-panel);
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 28px;
  box-shadow: 0 14px 24px rgba(31, 42, 44, 0.08);
}

@media (max-width: 900px) {
  .auth-layout {
    grid-template-columns: 1fr;
    padding: 18px;
  }

  .hero {
    padding: 26px;
  }

  .card {
    padding: 20px;
  }
}
</style>
