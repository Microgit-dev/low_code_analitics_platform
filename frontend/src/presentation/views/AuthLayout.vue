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
    radial-gradient(circle at 82% 18%, rgba(255, 255, 255, 0.24) 0%, transparent 38%),
    linear-gradient(140deg, #1e63d8 0%, #2f76ea 48%, #33a6b1 100%);
  border-radius: 22px;
  padding: 42px;
  border: 1px solid rgba(255, 255, 255, 0.26);
  box-shadow: 0 24px 40px rgba(34, 60, 120, 0.27);
  color: #edf5ff;
}

.hero h1 {
  margin: 0;
  font-size: clamp(2rem, 6vw, 3.2rem);
  line-height: 1.05;
}

.hero p {
  margin-top: 16px;
  max-width: 480px;
  color: #d8e7ff;
}

.card {
  background: var(--bg-panel);
  border: 1px solid var(--line);
  border-radius: 22px;
  padding: 28px;
  box-shadow: var(--shadow-soft);
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
