import React, { useEffect, useState } from "react";
import {
  Alert, Box, Divider, Flex, Heading, Link, LoadingSpinner, Statistics,
  StatisticsItem, Tag, Text, hubspot,
} from "@hubspot/ui-extensions";

// Renders the district intelligence this platform writes onto the company
// record: funding profile, ICP target profiles, buying signals, outreach.
hubspot.extend(({ context, runServerlessFunction, actions }) => (
  <DistrictIntelligence context={context} fetchProperties={actions.fetchCrmObjectProperties} />
));

const PROPERTIES = [
  "name", "website", "k12_icp_score", "k12_signal_strength", "k12_recommended_action",
  "k12_icp_profile_count", "k12_icp_profile_tags", "k12_enrollment", "k12_school_count",
  "k12_title_i_amount", "k12_lcff_supp_conc", "k12_frpm_pct", "k12_ela_proficient_pct",
  "k12_chronic_absent_rate", "k12_ell_pct", "k12_sped_pct", "k12_fed_rev_per_pupil",
  "k12_top_signal", "k12_buying_signals", "k12_outreach_status", "k12_researched_at",
  "k12_sis", "k12_lms", "k12_county", "k12_urbanicity", "k12_nces_id",
];

const num = (v) => {
  const f = parseFloat(v);
  return isNaN(f) ? null : f;
};
const money = (v) => {
  const f = num(v);
  if (f === null || f <= 0) return "—";
  return f >= 1e6 ? `$${(f / 1e6).toFixed(1)}M` : `$${Math.round(f).toLocaleString()}`;
};
const pct = (v) => (num(v) === null ? "—" : `${num(v).toFixed(1)}%`);
const int = (v) => (num(v) === null ? "—" : Math.round(num(v)).toLocaleString());

// ICP count -> visual weight. 4+ profiles is a hot account.
const icpVariant = (count) => (count >= 4 ? "error" : count >= 2 ? "warning" : "default");
const strengthVariant = (s) =>
  ({ HIGH: "error", MEDIUM: "warning", LOW: "success" }[String(s || "").toUpperCase()] || "default");

function DistrictIntelligence({ fetchProperties }) {
  const [props, setProps] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchProperties(PROPERTIES)
      .then(setProps)
      .catch((e) => setError(String(e)));
  }, []);

  if (error) return <Alert title="Could not load district intelligence">{error}</Alert>;
  if (!props) return <LoadingSpinner label="Loading district intelligence" />;

  const icpCount = num(props.k12_icp_profile_count) || 0;
  const researched = !!props.k12_researched_at;
  const tags = (props.k12_icp_profile_tags || "").split(" · ").filter((t) => t && t !== "—");
  const signals = (props.k12_buying_signals || "")
    .split("\n")
    .map((s) => s.trim())
    .filter(Boolean);

  return (
    <Flex direction="column" gap="medium">
      {/* Targeting summary */}
      <Flex direction="row" justify="between" align="center" wrap="wrap" gap="small">
        <Flex direction="row" gap="small" align="center">
          <Tag variant={icpVariant(icpCount)}>{icpCount} of 6 ICP profiles</Tag>
          {props.k12_signal_strength && (
            <Tag variant={strengthVariant(props.k12_signal_strength)}>
              {props.k12_signal_strength} signal
            </Tag>
          )}
          {props.k12_recommended_action && <Tag>{props.k12_recommended_action}</Tag>}
        </Flex>
        {researched ? (
          <Text variant="microcopy">AI researched {props.k12_researched_at}</Text>
        ) : (
          <Text variant="microcopy">Scored from public data — not yet researched</Text>
        )}
      </Flex>

      {tags.length > 0 && (
        <Flex direction="row" gap="extra-small" wrap="wrap">
          {tags.map((t) => (
            <Tag key={t} variant="default">{t}</Tag>
          ))}
        </Flex>
      )}

      <Divider />

      {/* Funding — why they can buy */}
      <Heading>Funding profile</Heading>
      <Statistics>
        <StatisticsItem label="Title I" number={money(props.k12_title_i_amount)}
                        labelIconName="dollarSign" />
        <StatisticsItem label="LCFF Supp+Conc" number={money(props.k12_lcff_supp_conc)} />
        <StatisticsItem label="Federal $/pupil" number={money(props.k12_fed_rev_per_pupil)} />
      </Statistics>

      {/* Need — why they should buy */}
      <Heading>Need indicators</Heading>
      <Statistics>
        <StatisticsItem label="Reading proficient" number={pct(props.k12_ela_proficient_pct)} />
        <StatisticsItem label="Free/reduced meals" number={pct(props.k12_frpm_pct)} />
        <StatisticsItem label="Chronic absence" number={pct(props.k12_chronic_absent_rate)} />
      </Statistics>

      <Text variant="microcopy">
        {int(props.k12_enrollment)} students · {int(props.k12_school_count)} schools ·{" "}
        {pct(props.k12_ell_pct)} EL · {pct(props.k12_sped_pct)} SPED
        {props.k12_county ? ` · ${props.k12_county}` : ""}
        {props.k12_urbanicity ? ` · ${props.k12_urbanicity}` : ""}
      </Text>

      {/* Signals — why now */}
      {props.k12_top_signal && (
        <>
          <Divider />
          <Heading>Buying signals</Heading>
          <Alert title="Top signal" variant="warning">{props.k12_top_signal}</Alert>
          {signals.slice(1, 5).map((s, i) => (
            <Text key={i}>• {s}</Text>
          ))}
        </>
      )}

      {/* Stack + outreach */}
      {(props.k12_sis || props.k12_lms || props.k12_outreach_status) && (
        <>
          <Divider />
          <Flex direction="row" gap="medium" wrap="wrap">
            {props.k12_sis && props.k12_sis !== "Unknown" && (
              <Text variant="microcopy">SIS: {props.k12_sis}</Text>
            )}
            {props.k12_lms && props.k12_lms !== "Unknown" && (
              <Text variant="microcopy">LMS: {props.k12_lms}</Text>
            )}
            {props.k12_outreach_status && (
              <Text variant="microcopy">Outreach: {props.k12_outreach_status}</Text>
            )}
            {props.k12_nces_id && (
              <Text variant="microcopy">NCES {props.k12_nces_id}</Text>
            )}
          </Flex>
        </>
      )}

      {props.website && (
        <Link href={props.website} external>District website</Link>
      )}
    </Flex>
  );
}
