"use client";

import { useEffect, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import { EMPTY_PROFILE_FORM, Profile, ProfileFormData } from "@/types/profile";
import ToolPageShell from "@/components/ToolPageShell";

const LIST_FIELDS = [
  { key: "work_experience", label: "İş Deneyimi", hint: "Her satıra bir deneyim yazın" },
  { key: "internship_experience", label: "Staj Deneyimi", hint: "Her satıra bir staj yazın" },
  { key: "technical_skills", label: "Teknik Beceriler", hint: "Virgülle ayırın" },
  { key: "certificates", label: "Sertifikalar", hint: "Virgülle ayırın" },
  { key: "projects", label: "Projeler", hint: "Her satıra bir proje yazın" },
] as const;

function listToText(key: (typeof LIST_FIELDS)[number]["key"], value: string[] | null): string {
  if (!value) return "";
  return key === "technical_skills" || key === "certificates"
    ? value.join(", ")
    : value.join("\n");
}

function textToList(key: (typeof LIST_FIELDS)[number]["key"], text: string): string[] {
  const separator = key === "technical_skills" || key === "certificates" ? "," : "\n";
  return text
    .split(separator)
    .map((s) => s.trim())
    .filter(Boolean);
}

export default function ProfilePage() {
  const [form, setForm] = useState<ProfileFormData>(EMPTY_PROFILE_FORM);
  const [listText, setListText] = useState<Record<string, string>>({});
  const [exists, setExists] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    apiFetch<Profile>("/profiles/me")
      .then((data) => {
        setForm(data);
        setListText(
          Object.fromEntries(
            LIST_FIELDS.map((f) => [f.key, listToText(f.key, data[f.key])]),
          ),
        );
        setExists(true);
      })
      .catch((e) => {
        if (e instanceof ApiError && e.status === 404) {
          setListText(Object.fromEntries(LIST_FIELDS.map((f) => [f.key, ""])));
        } else {
          setError(e instanceof ApiError ? e.message : "Profil yüklenemedi");
        }
      })
      .finally(() => setLoading(false));
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSaved(false);

    const payload: ProfileFormData = {
      ...form,
      ...Object.fromEntries(
        LIST_FIELDS.map((f) => [f.key, textToList(f.key, listText[f.key] ?? "")]),
      ),
    };

    try {
      if (exists) {
        await apiFetch<Profile>("/profiles/me", {
          method: "PATCH",
          body: JSON.stringify(payload),
        });
      } else {
        await apiFetch<Profile>("/profiles", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        setExists(true);
      }
      setSaved(true);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Profil kaydedilemedi");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <p className="p-8 text-center text-sm text-gray-500">Yükleniyor…</p>;
  }

  return (
    <ToolPageShell index="01" title="Kariyer Profili" description="Tüm analiz ve önerilerin temelini oluşturan deneyim, beceri ve hedef sinyallerini yönet.">
      <div className="mx-auto max-w-3xl">
      <form
        onSubmit={handleSubmit}
        className="mt-6 space-y-4 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-900"
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
              Eğitim Seviyesi
            </label>
            <input
              value={form.education_level ?? ""}
              onChange={(e) => setForm({ ...form, education_level: e.target.value })}
              placeholder="Örn: Lisans"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
              Bölüm
            </label>
            <input
              value={form.department ?? ""}
              onChange={(e) => setForm({ ...form, department: e.target.value })}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
              Üniversite
            </label>
            <input
              value={form.university ?? ""}
              onChange={(e) => setForm({ ...form, university: e.target.value })}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
              Mezuniyet Yılı
            </label>
            <input
              type="number"
              min={1950}
              max={2035}
              value={form.graduation_year ?? ""}
              onChange={(e) =>
                setForm({
                  ...form,
                  graduation_year: e.target.value ? Number(e.target.value) : null,
                })
              }
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
              İngilizce Seviyesi
            </label>
            <input
              value={form.english_level ?? ""}
              onChange={(e) => setForm({ ...form, english_level: e.target.value })}
              placeholder="Örn: B2"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
              Hedef Şehir
            </label>
            <input
              value={form.target_city ?? ""}
              onChange={(e) => setForm({ ...form, target_city: e.target.value })}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
            />
          </div>
          <div className="sm:col-span-2">
            <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
              Çalışma Şekli Tercihi
            </label>
            <select
              value={form.work_mode_preference ?? ""}
              onChange={(e) =>
                setForm({
                  ...form,
                  work_mode_preference: (e.target.value || null) as ProfileFormData["work_mode_preference"],
                })
              }
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
            >
              <option value="">Belirtilmedi</option>
              <option value="remote">Uzaktan</option>
              <option value="hybrid">Hibrit</option>
              <option value="office">Ofisten</option>
            </select>
          </div>
        </div>

        {LIST_FIELDS.map((field) => (
          <div key={field.key}>
            <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
              {field.label} <span className="font-normal text-gray-400">({field.hint})</span>
            </label>
            <textarea
              rows={field.key === "technical_skills" || field.key === "certificates" ? 2 : 3}
              value={listText[field.key] ?? ""}
              onChange={(e) => setListText({ ...listText, [field.key]: e.target.value })}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
            />
          </div>
        ))}

        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
            Kariyer Hedefi
          </label>
          <textarea
            rows={3}
            value={form.career_goal ?? ""}
            onChange={(e) => setForm({ ...form, career_goal: e.target.value })}
            placeholder="Ulaşmak istediğiniz pozisyon ve hedefinizi kısaca yazın…"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
          />
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}
        {saved && <p className="text-sm text-green-600">✓ Profil kaydedildi</p>}

        <button
          type="submit"
          disabled={saving}
          className="w-full rounded-lg bg-blue-600 py-2.5 text-sm font-medium text-white transition hover:bg-blue-700 disabled:opacity-50"
        >
          {saving ? "Kaydediliyor…" : "Profili Kaydet"}
        </button>
      </form>
      </div>
    </ToolPageShell>
  );
}
