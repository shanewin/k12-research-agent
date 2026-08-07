import React, { useEffect, useState } from "react";
import {
  Alert, Divider, Flex, LoadingSpinner, Statistics, StatisticsItem, Tag, Text, hubspot,
} from "@hubspot/ui-extensions";

// Compact sidebar variant — the same intelligence, sized for the right rail.
hubspot.extend(({ actions }) => <DistrictSummary fetchProperties={actions.fetchCrmObjectProperties} />);

const PROPERTIES = [
  "k12_icp_profile_count", "k12_icp_profile_tags", "k12_signal_strength",
  "k12_recommended_action", "k12_title_i_amount", "k12_lcff_supp_conc",
  "k12_ela_proficient_pct", "k12_frpm_pct", "k12_enrollment",
  "k12_top_signal", "k12_outreach_status", "k12_researched_at",
];

const num = (v) => { const f = parseFloat(v); return isNaN(f) ? null : f; };
const money = (v) => { const f = num(v); return f && f > 0 ? (f >= 1e6 ? `$${(f / 1e6).toFixed(1)}M` : `$${Math.round(f).toLocaleString()}`) : "—"; };
const pct = (v) => (num(v) === null ? "—" : `${num(v).toFixed(1)}%`);

function DistrictSummary({ fetchProperties }) {
  const [p, setP] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    fetchProperties(PROPERTIES).then(setP).catch((e) => setErr(String(e)));
  }, []);

  if (err) return <Alert title="Could not load">{err}</Alert>;
  if (!p) return <LoadingSpinner label="Loading" />;

  const icp = num(p.k12_icp_profile_count) || 0;
  const tags = (p.k12_icp_profile_tags || "").split(" · ").filter((t) => t && t !== "—");

  return (
    <Flex direction="column" gap="small">
      <Flex direction="row" gap="extra-small" wrap="wrap">
        <Tag variant={icp >= 4 ? "error" : icp >= 2 ? "warning" : "default"}>
          ICP {icp}/6
        </Tag>
        {p.k12_signal_strength && <Tag>{p.k12_signal_strength}</Tag>}
        {p.k12_recommended_action && <Tag>{p.k12_recommended_action}</Tag>}
      </Flex>

      <Statistics>
        <StatisticsItem label="Title I" number={money(p.k12_title_i_amount)} />
        <StatisticsItem label="LCFF S+C" number={money(p.k12_lcff_supp_conc)} />
      </Statistics>
      <Statistics>
        <StatisticsItem label="Reading" number={pct(p.k12_ela_proficient_pct)} />
        <StatisticsItem label="FRPM" number={pct(p.k12_frpm_pct)} />
      </Statistics>

      {tags.length > 0 && (
        <>
          <Divider />
          <Text variant="microcopy">Matched profiles</Text>
          <Flex direction="row" gap="extra-small" wrap="wrap">
            {tags.map((t) => <Tag key={t}>{t}</Tag>)}
          </Flex>
        </>
      )}

      {p.k12_top_signal && (
        <>
          <Divider />
          <Alert title="Top buying signal" variant="warning">{p.k12_top_signal}</Alert>
        </>
      )}

      {p.k12_outreach_status && <Text variant="microcopy">{p.k12_outreach_status}</Text>}
    </Flex>
  );
}
