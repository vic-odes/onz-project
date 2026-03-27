import Stepper from "@/components/Stepper";

export default function NouveauProjetPage() {
  return (
    <div className="py-12 px-6">
      <div className="max-w-2xl mx-auto mb-8 text-center">
        <h1 className="font-playfair text-4xl font-bold text-bleu-marine mb-3">
          Nouveau projet
        </h1>
        <p className="font-source text-gray-600">
          Complétez les 5 étapes ci-dessous pour générer votre document de projet professionnel.
        </p>
      </div>
      <Stepper />
    </div>
  );
}
