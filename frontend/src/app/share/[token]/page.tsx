"use client";

import { use, useEffect, useState } from "react";
import { ShieldCheck } from "lucide-react";
import { API_BASE, ApiError, apiFetch } from "@/lib/api";
import AtsResultCard from "@/components/AtsResultCard";
import { AtsAnalysis } from "@/types/ats";

interface SharedResumeView {
  resume_title: string;
  parsed_json: {
    personal_info: { name: string | null; email: string | null; phone: string | null };
    education: { school: string; department: string; start_date: string | null; end_date: string | null; gpa: string | null }[];
    experience: { company: string; role: string; start_date: string | null; end_date: string | null; description: string }[];
    projects: { name: string; description: string; technologies: string[]; link: string | null }[];
    skills: string[];
    certificates: string[];
    languages: { language: string; level: string | null }[];
  } | null;
  latest_ats_analysis: AtsAnalysis | null;
  shared_at: string;
}

export default function SharedResumePage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = use(params);
  const [data, setData] = useState<SharedResumeView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch<SharedResumeView>(`/share/resumes/${token}`, { headers: {} })
      .then(setData)
      .catch((e) =>
        setError(e instanceof ApiError ? e.message : "Paylaşım yüklenemedi"),
      )
      .finally(() => setLoading(false));
  }, [token]);

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#10121c] text-sm text-gray-400">
        Yükleniyor…
      </main>
    );
  }

  if (error || !data) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#10121c] px-4 text-center">
        <div className="max-w-sm rounded-2xl border border-white/10 bg-white/[.03] p-6">
          <p className="text-sm text-gray-300">{error ?? "Paylaşım bulunamadı."}</p>
        </div>
      </main>
    );
  }

  const content = data.parsed_json;

  return (
    <main className="min-h-screen bg-[#10121c] px-4 py-10 sm:px-8">
      <div className="mx-auto max-w-2xl">
        <div className="mb-6 flex items-center justify-between gap-3 rounded-xl border border-white/10 bg-white/[.03] px-4 py-3 text-xs text-gray-400">
          <span className="flex items-center gap-2">
            <ShieldCheck size={14} className="text-teal-400" />
            Salt okunur paylaşım · düzenlenemez
          </span>
          <span>{new Date(data.shared_at).toLocaleDateString("tr-TR")}den beri paylaşılıyor</span>
        </div>

        {content && (
          <div className="rounded-2xl border border-white/10 bg-white p-6 text-gray-900 shadow-sm dark:bg-gray-950 dark:text-gray-100">
            <h1 className="text-2xl font-bold">{content.personal_info.name ?? data.resume_title}</h1>
            <p className="text-sm text-gray-500">
              {[content.personal_info.email, content.personal_info.phone].filter(Boolean).join(" · ")}
            </p>

            {content.experience.length > 0 && (
              <Section title="Deneyim">
                {content.experience.map((exp, i) => (
                  <div key={i} className="mb-2">
                    <p className="text-sm font-semibold">
                      {exp.role} · {exp.company}
                      <span className="ml-2 font-normal text-gray-400">
                        {[exp.start_date, exp.end_date ?? "Halen"].filter(Boolean).join(" – ")}
                      </span>
                    </p>
                    <p className="text-sm text-gray-700 dark:text-gray-300">{exp.description}</p>
                  </div>
                ))}
              </Section>
            )}

            {content.education.length > 0 && (
              <Section title="Eğitim">
                {content.education.map((edu, i) => (
                  <p key={i} className="text-sm text-gray-700 dark:text-gray-300">
                    <span className="font-semibold">{edu.school}</span> — {edu.department}
                    {edu.gpa ? ` (GPA: ${edu.gpa})` : ""}
                    <span className="ml-2 text-gray-400">
                      {[edu.start_date, edu.end_date].filter(Boolean).join(" – ")}
                    </span>
                  </p>
                ))}
              </Section>
            )}

            {content.projects.length > 0 && (
              <Section title="Projeler">
                {content.projects.map((p, i) => (
                  <p key={i} className="text-sm text-gray-700 dark:text-gray-300">
                    <span className="font-semibold">{p.name}:</span> {p.description}
                    {p.technologies.length > 0 && (
                      <span className="text-gray-400"> ({p.technologies.join(", ")})</span>
                    )}
                  </p>
                ))}
              </Section>
            )}

            {content.skills.length > 0 && (
              <Section title="Beceriler">
                <div className="flex flex-wrap gap-1.5">
                  {content.skills.map((skill) => (
                    <span
                      key={skill}
                      className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-700 dark:bg-gray-800 dark:text-gray-300"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              </Section>
            )}

            {content.certificates.length > 0 && (
              <Section title="Sertifikalar">
                {content.certificates.map((c) => (
                  <p key={c} className="text-sm text-gray-700 dark:text-gray-300">{c}</p>
                ))}
              </Section>
            )}

            {content.languages.length > 0 && (
              <Section title="Diller">
                {content.languages.map((l, i) => (
                  <p key={i} className="text-sm text-gray-700 dark:text-gray-300">
                    {l.language}
                    {l.level ? ` — ${l.level}` : ""}
                  </p>
                ))}
              </Section>
            )}
          </div>
        )}

        {data.latest_ats_analysis && (
          <div className="mt-6">
            <AtsResultCard analysis={data.latest_ats_analysis} />
          </div>
        )}
      </div>
    </main>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mt-4">
      <h3 className="mb-1 border-b border-gray-200 pb-0.5 text-xs font-bold uppercase tracking-wider text-gray-500 dark:border-gray-700">
        {title}
      </h3>
      {children}
    </div>
  );
}
