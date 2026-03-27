import Link from "next/link";

const features = [
  {
    icon: "🌍",
    title: "Cadre Logique",
    desc: "Génération automatique du LogFrame avec objectifs SMART, résultats et indicateurs.",
  },
  {
    icon: "📊",
    title: "Budget Détaillé",
    desc: "Lignes budgétaires structurées avec analyse coût-bénéfice et VAN.",
  },
  {
    icon: "⚠️",
    title: "Matrice des Risques",
    desc: "Identification et plan d'atténuation des risques projet.",
  },
  {
    icon: "📄",
    title: "Export Word",
    desc: "Document .docx professionnel prêt à soumettre aux bailleurs.",
  },
];

const bailleurs = ["AFD", "Union Européenne", "Banque Mondiale", "PNUD"];
const secteurs = [
  "Santé",
  "Éducation",
  "Agriculture",
  "Environnement",
  "Eau & Assainissement",
  "Gouvernance",
];

export default function HomePage() {
  return (
    <div className="flex flex-col">
      {/* Hero */}
      <section className="bg-bleu-marine text-white py-24 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <p className="text-vert-sauge font-source font-semibold uppercase tracking-widest text-sm mb-4">
            Assistant IA de montage de projets
          </p>
          <h1 className="font-playfair text-5xl font-bold leading-tight mb-6">
            Générez des documents de projets
            <br />
            <span className="text-vert-sauge">de développement international</span>
          </h1>
          <p className="font-source text-lg text-gray-300 mb-10 max-w-2xl mx-auto">
            Remplissez un formulaire guidé et obtenez en quelques secondes un document Word
            professionnel — cadre logique, budget, analyse des risques — prêt à soumettre
            à vos bailleurs.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link href="/nouveau-projet" className="btn-accent text-center">
              Créer un nouveau projet
            </Link>
            <Link href="/mes-projets" className="btn-secondary text-center">
              Mes projets sauvegardés
            </Link>
          </div>
        </div>
      </section>

      {/* Fonctionnalités */}
      <section className="py-20 px-6 bg-creme">
        <div className="max-w-5xl mx-auto">
          <h2 className="font-playfair text-3xl font-bold text-bleu-marine text-center mb-12">
            Tout ce dont vous avez besoin
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map((f) => (
              <div key={f.title} className="card text-center hover:shadow-lg transition-shadow">
                <div className="text-4xl mb-4">{f.icon}</div>
                <h3 className="font-playfair text-lg font-semibold text-bleu-marine mb-2">
                  {f.title}
                </h3>
                <p className="font-source text-sm text-gray-600">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Bailleurs & Secteurs */}
      <section className="py-16 px-6 bg-white">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="font-playfair text-2xl font-bold text-bleu-marine mb-8">
            Adapté aux standards de vos bailleurs
          </h2>
          <div className="flex flex-wrap justify-center gap-4 mb-10">
            {bailleurs.map((b) => (
              <span
                key={b}
                className="bg-bleu-marine text-white px-4 py-2 rounded-full font-source font-semibold text-sm"
              >
                {b}
              </span>
            ))}
          </div>
          <h3 className="font-playfair text-xl font-semibold text-bleu-marine mb-6">
            Secteurs couverts
          </h3>
          <div className="flex flex-wrap justify-center gap-3">
            {secteurs.map((s) => (
              <span
                key={s}
                className="bg-vert-sauge bg-opacity-10 text-vert-sauge border border-vert-sauge
                           px-4 py-2 rounded-full font-source text-sm font-semibold"
              >
                {s}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 px-6 bg-vert-sauge text-white text-center">
        <div className="max-w-2xl mx-auto">
          <h2 className="font-playfair text-3xl font-bold mb-4">
            Prêt à commencer ?
          </h2>
          <p className="font-source text-lg mb-8 text-green-100">
            Votre premier document en moins de 2 minutes.
          </p>
          <Link href="/nouveau-projet" className="bg-white text-vert-sauge px-8 py-4 rounded-lg font-source font-bold hover:bg-opacity-90 transition-all">
            Démarrer maintenant
          </Link>
        </div>
      </section>
    </div>
  );
}
