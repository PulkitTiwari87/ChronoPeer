import { Chip } from "./ui";

const KIND = {
  proposed: "neutral",
  challenged: "warn",
  agreed: "ok",
  revised: "accent",
  retained: "ok",
  unresolved: "warn",
  withdrawn: "bad",
  known: "ok",
  assumed: "warn",
  unknown: "warn",
  invalid: "bad",
  missing: "bad",
  agree: "ok",
  challenge: "warn",
  accepted: "accent",
  partially_accepted: "accent",
  rejected: "neutral",
  modified: "accent",
};

export default function StatusBadge({ value }) {
  return <Chip kind={KIND[value] || "neutral"}>{String(value).replace(/_/g, " ")}</Chip>;
}
