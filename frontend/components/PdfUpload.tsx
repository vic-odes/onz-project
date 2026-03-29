"use client";
import { useRef, useState } from "react";

const MAX_FILES = 3;
const MAX_SIZE_MB = 10;
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;

interface PdfFile {
  name: string;
  sizeKb: number;
  b64: string; // base64 sans préfixe data:
}

interface PdfUploadProps {
  files: PdfFile[];
  onChange: (files: PdfFile[]) => void;
}

function readFileAsBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      // Supprimer le préfixe "data:application/pdf;base64,"
      const b64 = result.split(",")[1];
      resolve(b64);
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

export default function PdfUpload({ files, onChange }: PdfUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const addFiles = async (fileList: FileList) => {
    setError(null);
    const incoming = Array.from(fileList);

    const remaining = MAX_FILES - files.length;
    if (remaining <= 0) {
      setError(`Maximum ${MAX_FILES} fichiers autorisés.`);
      return;
    }

    const toProcess = incoming.slice(0, remaining);
    const newPdfFiles: PdfFile[] = [];

    for (const file of toProcess) {
      if (file.type !== "application/pdf") {
        setError("Seuls les fichiers PDF sont acceptés.");
        continue;
      }
      if (file.size > MAX_SIZE_BYTES) {
        setError(`"${file.name}" dépasse ${MAX_SIZE_MB} Mo.`);
        continue;
      }
      // Vérifier doublon par nom
      if (files.some((f) => f.name === file.name)) continue;

      try {
        const b64 = await readFileAsBase64(file);
        newPdfFiles.push({ name: file.name, sizeKb: Math.round(file.size / 1024), b64 });
      } catch {
        setError(`Impossible de lire "${file.name}".`);
      }
    }

    if (newPdfFiles.length > 0) onChange([...files, ...newPdfFiles]);
  };

  const removeFile = (index: number) => {
    setError(null);
    onChange(files.filter((_, i) => i !== index));
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Zone de dépôt */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false); addFiles(e.dataTransfer.files); }}
        onClick={() => inputRef.current?.click()}
        className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
          ${dragging ? "border-vert-sauge bg-green-50" : "border-gray-300 hover:border-bleu-marine hover:bg-gray-50"}
          ${files.length >= MAX_FILES ? "opacity-50 pointer-events-none" : ""}`}
      >
        <div className="text-3xl mb-2">📄</div>
        <p className="font-source font-semibold text-bleu-marine text-sm">
          Glissez vos PDFs ici ou cliquez pour sélectionner
        </p>
        <p className="font-source text-xs text-gray-400 mt-1">
          PDF uniquement — max {MAX_FILES} fichiers, {MAX_SIZE_MB} Mo chacun
        </p>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          multiple
          className="hidden"
          onChange={(e) => e.target.files && addFiles(e.target.files)}
        />
      </div>

      {/* Message d'erreur */}
      {error && (
        <p className="font-source text-sm text-red-500">{error}</p>
      )}

      {/* Liste des fichiers */}
      {files.length > 0 && (
        <ul className="flex flex-col gap-2">
          {files.map((f, i) => (
            <li
              key={i}
              className="flex items-center justify-between bg-gray-50 border border-gray-200 rounded-lg px-4 py-3"
            >
              <div className="flex items-center gap-3 min-w-0">
                <span className="text-lg">📎</span>
                <div className="min-w-0">
                  <p className="font-source text-sm font-semibold text-bleu-marine truncate">{f.name}</p>
                  <p className="font-source text-xs text-gray-400">{f.sizeKb} Ko</p>
                </div>
              </div>
              <button
                onClick={() => removeFile(i)}
                className="text-gray-400 hover:text-red-500 font-bold text-xl px-2 flex-shrink-0"
                title="Supprimer"
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}

      {files.length > 0 && (
        <p className="font-source text-xs text-vert-sauge font-semibold">
          ✓ {files.length} document{files.length > 1 ? "s" : ""} — l&apos;IA analysera leur contenu pour enrichir le projet
        </p>
      )}
    </div>
  );
}
