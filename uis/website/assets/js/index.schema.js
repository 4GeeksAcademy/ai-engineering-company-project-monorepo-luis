const organizationSchema = {
  "@context": "https://schema.org",
  "@type": "Organization",
  name: "Nexova",
  description: "Consultora de recursos humanos y adquisición de talento",
  url: "https://nexova.com",
  foundingDate: "2011",
  address: [
    {
      "@type": "PostalAddress",
      addressCountry: "ES",
      addressLocality: "Valencia",
      addressRegion: "Comunidad Valenciana"
    },
    {
      "@type": "PostalAddress",
      addressCountry: "US",
      addressLocality: "Miami",
      addressRegion: "Florida"
    }
  ],
  contactPoint: {
    "@type": "ContactPoint",
    telephone: "+34-960-123-456",
    contactType: "customer service",
    availableLanguage: ["Spanish", "English"]
  },
  sameAs: [
    "https://linkedin.com/company/nexova",
    "https://instagram.com/nexova"
  ]
};

const schemaScript = document.createElement("script");
schemaScript.type = "application/ld+json";
schemaScript.text = JSON.stringify(organizationSchema);
document.head.appendChild(schemaScript);
