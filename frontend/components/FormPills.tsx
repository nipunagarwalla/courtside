// `results` comes from the API most-recent-first; render most recent on the right.
export default function FormPills({ results }: { results: string[] }) {
  const ordered = [...results].reverse();
  return (
    <div className="flex gap-1">
      {ordered.map((r, i) => (
        <span
          key={i}
          className={`inline-flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold text-white ${
            r === "W" ? "bg-green-600" : "bg-red-600"
          }`}
        >
          {r}
        </span>
      ))}
    </div>
  );
}
