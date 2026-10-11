import { mockCpiInflation, mockGdpGrowth } from './mock-data';
import type { PolicyAlternative, SimulatorInputs, SimulatorResult } from './types';

export const policyAlternatives: Array<{ id: PolicyAlternative; label: string; basisPoints: number }> = [
	{ id: 'hike-50', label: 'Hike 50 bp', basisPoints: 50 },
	{ id: 'hold', label: 'Hold', basisPoints: 0 },
	{ id: 'cut-25', label: 'Cut 25 bp', basisPoints: -25 },
];

export const defaultSimulatorInputs: SimulatorInputs = {
	oilPriceShock: 0,
	inrShock: 0,
	foodInflationShock: 0,
	policyRateChangeBp: 0,
	horizonMonths: 6,
	policyAlternative: 'hold',
};

export function calculateDemoSimulation(inputs: SimulatorInputs): SimulatorResult {
	const horizonFactor = 1 + inputs.horizonMonths / 24;
	const oilEffect = inputs.oilPriceShock * 0.012;
	const currencyEffect = -inputs.inrShock * 0.018;
	const foodEffect = inputs.foodInflationShock * 0.62;
	const policyEffect = -(inputs.policyRateChangeBp / 100) * 0.12;
	const scenarioInflation = Number((mockCpiInflation.value + (oilEffect + currencyEffect + foodEffect + policyEffect) * horizonFactor).toFixed(2));
	const potentialGrowthImpact = Number((-(Math.abs(inputs.policyRateChangeBp) / 100) * 0.18 - Math.abs(inputs.oilPriceShock) * 0.004 - Math.abs(inputs.inrShock) * 0.006 - Math.abs(inputs.foodInflationShock) * 0.02).toFixed(2));
	const fxPressure = Number(Math.min(100, Math.max(0, Math.abs(inputs.inrShock) * 9 + Math.abs(inputs.oilPriceShock) * 1.4)).toFixed(0));
	const uncertainty = Number((0.45 + inputs.horizonMonths * 0.045 + Math.abs(inputs.oilPriceShock) * 0.008 + Math.abs(inputs.inrShock) * 0.012 + Math.abs(inputs.foodInflationShock) * 0.06).toFixed(2));
	const distribution = [-1, -0.5, 0, 0.5, 1].map((offset) => Number((scenarioInflation + offset * uncertainty).toFixed(2)));
	const inflationScore = Math.max(0, Math.min(100, Math.round(82 - Math.abs(scenarioInflation - 4) * 14)));
	const growthScore = Math.max(0, Math.min(100, Math.round(78 + potentialGrowthImpact * 7)));
	const stabilityScore = Math.max(0, Math.min(100, Math.round(88 - fxPressure * 0.45)));

	return {
		baselineInflation: mockCpiInflation.value,
		scenarioInflation,
		potentialGrowthImpact,
		fxPressure,
		uncertainty,
		distribution,
		policyScorecard: [
			{ dimension: 'Inflation alignment', score: inflationScore, status: 'mock', rationale: 'Deterministic demo score based on distance from the illustrative 4% reference.', confidence: 0.58 },
			{ dimension: 'Growth trade-off', score: growthScore, status: potentialGrowthImpact < -0.3 ? 'warning' : 'mock', rationale: 'Demo score reflects the direction and size of the configured policy and shock inputs.', confidence: 0.55 },
			{ dimension: 'External stability', score: stabilityScore, status: fxPressure > 45 ? 'warning' : 'mock', rationale: 'Demo score responds to configured INR and oil shock magnitudes.', confidence: 0.52 },
		],
		interpretation: `This deterministic demo path moves inflation from ${mockCpiInflation.value.toFixed(1)}% to ${scenarioInflation.toFixed(2)}% over ${inputs.horizonMonths} months. It is not an econometric result.`,
		isDemo: true,
	};
}

export const baselineGrowth = mockGdpGrowth.value;