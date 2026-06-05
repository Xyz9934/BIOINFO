import 'package:flutter_test/flutter_test.dart';

import 'package:bioinfo_student_app/main.dart';

void main() {
  testWidgets('App renders project title', (WidgetTester tester) async {
    await tester.pumpWidget(const BioinformaticsApp());

    expect(find.text('Bioinformatics Explorer'), findsOneWidget);
    expect(find.text('DNA Sequence Analyzer'), findsOneWidget);
    expect(find.text('Disease to Gene Search'), findsOneWidget);
  });
}
