import '../../character/models/character.dart';
import '../../creative/models/creative_style.dart';
import '../../scene/models/scene.dart';

import '../models/image_prompt.dart';

class ImagePromptBuilder {
  static ImagePrompt build({
    required Character character,
    required CreativeStyle creative,
    required Scene scene,
    required Map<String, dynamic> product,
  }) {
  
    final positiveParts = <String>[
      character.basePrompt,
      ...creative.prompt.values.cast<String>(),
      ...scene.prompt.values.cast<String>(),
    ];

    final productName = product['name'];

    if (productName != null &&
        productName.toString().isNotEmpty) {
      positiveParts.add(productName.toString());
    }

    final positivePrompt = positiveParts.join(', ');

    final negativePrompt =
        creative.negativePrompt.join(', ');

    return ImagePrompt(
      positivePrompt: positivePrompt,
      negativePrompt: negativePrompt,
      metadata: {
        'character': character.id,
        'creative': creative.id,
        'scene': scene.id,
        'productId': product['id'],
      },
    );
  }
}
    );
  }
}