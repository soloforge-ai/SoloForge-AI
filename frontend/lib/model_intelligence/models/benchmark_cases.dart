import 'benchmark_case.dart';

const imageBenchmarkCases = <BenchmarkCase>[
  BenchmarkCase(
    id: 'character-consistency',
    name: 'Character Consistency',
    description: 'Evaluate identity preservation against a fixed character reference.',
    prompt: 'Create a premium commercial portrait of the referenced character standing confidently in a cinematic studio environment. Preserve the character identity, facial structure, clothing design, proportions, and recognizable visual traits. Clean composition, realistic materials, professional advertising photography.',
  ),
  BenchmarkCase(
    id: 'product-commercial',
    name: 'Product Commercial',
    description: 'Evaluate product fidelity, composition, and commercial readiness.',
    prompt: 'Create a premium product advertisement using the referenced product as the exact visual source. Preserve product shape, proportions, materials, colors, logos, and distinctive details. Place it in a sophisticated commercial scene with strong visual hierarchy, realistic lighting, clean composition, and polished advertising quality.',
  ),
  BenchmarkCase(
    id: 'text-in-image',
    name: 'Text in Image',
    description: 'Evaluate typography rendering and layout adherence.',
    prompt: 'Create a premium vertical social media advertisement. Include the exact headline: "THE BIGGEST VISION." Render the headline clearly and accurately with professional typography, strong hierarchy, generous negative space, cinematic lighting, and a polished commercial layout.',
  ),
];
