export default function WLBadge({ result }: { result: "W" | "L" }) {
  return (
    <span
      className={`inline-flex h-6 w-6 items-center justify-center rounded text-xs font-bold text-white ${
        result === "W" ? "bg-green-600" : "bg-red-600"
      }`}
    >
      {result}
    </span>
  );
}
