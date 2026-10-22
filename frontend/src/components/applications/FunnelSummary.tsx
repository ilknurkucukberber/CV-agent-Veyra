"use client";

import { useEffect, useState } from "react";
import { Info } from "lucide-react";
import { apiFetch } from "@/lib/api";

interface FunnelStage {
  key: string;
  label: string;
  count: number;
}

interface FunnelConversion {
  from_key: string;
  to_key: string;
  from_label: string;
  to_label: string;
  rate: number | null;
}

interface FunnelData {
  stages: FunnelStage[];
  conversions: FunnelConversion[];
  rejected_count: number;
  total_count: number;
  note: string;
}

export default function FunnelSummary() {
  const [data, setData] = useState<FunnelData | null>(null);

  useEffect(() => {
    apiFetch<FunnelData>("/applications/analytics/funnel")
      .then(setData)
      .catch(() => setData(null));
  }, []);

  if (!data || data.total_count === 0) return null;

  const maxCount = data.stages[0]?.count || 1;

  return (
    <section className="funnel-summary">
      <div className="funnel-summary-head">
        <h2>Başvuru hunisi</h2>
        <span className="funnel-summary-total">{data.total_count} başvuru · {data.rejected_count} olumsuz</span>
      </div>

      <div className="funnel-summary-stages">
        {data.stages.map((stage, i) => {
          const conversion = data.conversions[i - 1];
          return (
            <div key={stage.key} className="funnel-stage">
              {i > 0 && (
                <span className="funnel-stage-rate">
                  {conversion?.rate !== null && conversion?.rate !== undefined
                    ? `%${Math.round(conversion.rate * 100)}`
                    : "—"}
                </span>
              )}
              <div className="funnel-stage-bar-track">
                <div
                  className="funnel-stage-bar"
                  style={{ width: `${Math.max((stage.count / maxCount) * 100, stage.count > 0 ? 6 : 0)}%` }}
                />
              </div>
              <div className="funnel-stage-meta">
                <span className="funnel-stage-label">{stage.label}</span>
                <span className="funnel-stage-count">{stage.count}</span>
              </div>
            </div>
          );
        })}
      </div>

      <p className="funnel-summary-note">
        <Info size={12} />
        {data.note}
      </p>
    </section>
  );
}
