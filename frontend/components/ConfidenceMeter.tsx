interface ConfidenceMeterProps {
	value: number;
}

export function ConfidenceMeter({ value }: ConfidenceMeterProps) {
	const clampedValue = Math.min(100, Math.max(0, value));

	return (
		<div aria-label={`Confidence ${clampedValue}%`} className="space-y-2">
			<div className="flex justify-between text-xs text-slate-500">
				<span>Confidence</span>
				<span>{clampedValue}%</span>
			</div>
			<div className="h-2 overflow-hidden rounded-full bg-slate-200">
				<div className="h-full rounded-full bg-teal-600" style={{ width: `${clampedValue}%` }} />
			</div>
		</div>
	);
}
