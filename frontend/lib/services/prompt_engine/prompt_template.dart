class PromptTemplate {
  final String system;

  final String instruction;

  final String style;

  const PromptTemplate({
    required this.system,
    required this.instruction,
    required this.style,
  });

  String build({required String content}) {
    return '''
$system

$instruction

Style:
$style

$content
''';
  }
}
