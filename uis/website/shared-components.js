class NexovaHeader extends HTMLElement {
  connectedCallback() {
    const currentPage = this.getAttribute("page") === "talent" ? "talent" : "home";
    const destinations = currentPage === "home"
      ? [
          { label: "Inicio", href: "./index.html", page: "home" },
          { label: "Servicios", href: "#servicios" },
          { label: "Talento", href: "./application.html#registro-talento" },
          { label: "Contacto", href: "#contacto" }
        ]
      : [
          { label: "Inicio", href: "./index.html", page: "home" },
          { label: "Servicios", href: "./index.html#servicios" },
          { label: "Talento", href: "#registro-talento", page: "talent" },
          { label: "Contacto", href: "./index.html#contacto" }
        ];

    this.innerHTML = `
      <header class="relative z-10 border-b border-white/10">
        <div class="mx-auto flex w-full max-w-6xl flex-col items-start gap-3 px-5 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-8">
          <a
            href="./index.html"
            class="text-xl font-extrabold tracking-tight text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-300 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950"
            aria-label="Nexova, volver al inicio"
          >
            Nexova
          </a>
          <nav class="w-full sm:w-auto" aria-label="Navegación principal">
            <ul class="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm font-medium sm:gap-6 sm:text-base">
              ${destinations.map(({ label, href, page }) => `
                <li>
                  <a
                    href="${href}"
                    ${page === currentPage ? 'aria-current="page"' : ""}
                    class="rounded-md px-1.5 py-1 text-slate-300 transition hover:text-brand-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-300 sm:px-2"
                  >
                    ${label}
                  </a>
                </li>
              `).join("")}
            </ul>
          </nav>
        </div>
      </header>
    `;
  }
}

class NexovaFooter extends HTMLElement {
  connectedCallback() {
    this.innerHTML = `
      <footer class="relative z-10 border-t border-white/10">
        <div class="mx-auto flex w-full max-w-6xl flex-col gap-4 px-5 py-6 text-sm text-slate-300 sm:flex-row sm:items-center sm:justify-between sm:px-8">
          <p>© 2025 Nexova. Todos los derechos reservados.</p>
          <nav class="flex items-center gap-3" aria-label="Redes sociales">
            <a href="https://linkedin.com/company/nexova" target="_blank" rel="noopener noreferrer" class="rounded px-1 py-0.5 text-slate-100 hover:text-brand-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-300">LinkedIn</a>
            <span aria-hidden="true">|</span>
            <a href="https://instagram.com/nexova" target="_blank" rel="noopener noreferrer" class="rounded px-1 py-0.5 text-slate-100 hover:text-brand-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-300">Instagram</a>
          </nav>
        </div>
      </footer>
    `;
  }
}

customElements.define("nexova-header", NexovaHeader);
customElements.define("nexova-footer", NexovaFooter);
