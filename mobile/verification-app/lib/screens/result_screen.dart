import 'package:flutter/material.dart';

import '../models/verification_result.dart';

/// SCR-06 마지막 단계: 얼굴 매칭 결과와 입장 승인/거부를 표시한다.
class ResultScreen extends StatelessWidget {
  const ResultScreen({super.key, required this.result});

  final VerificationResult result;

  @override
  Widget build(BuildContext context) {
    final matchPercent = (result.faceMatchScore * 100).toStringAsFixed(1);
    final approved = result.faceMatchResult && !result.duplicateScanFlag;

    return Scaffold(
      appBar: AppBar(title: const Text('검표 결과')),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              approved ? Icons.check_circle : Icons.cancel,
              color: approved ? Colors.green : Colors.red,
              size: 96,
            ),
            const SizedBox(height: 16),
            Text(
              approved ? '입장 승인' : '입장 거부',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 8),
            Text('MATCH $matchPercent%', style: Theme.of(context).textTheme.titleLarge),
            if (result.duplicateScanFlag)
              const Padding(
                padding: EdgeInsets.only(top: 8),
                child: Text(
                  '이미 입장 처리된 QR 코드입니다 (중복 사용 의심)',
                  style: TextStyle(color: Colors.red),
                ),
              ),
            const SizedBox(height: 32),
            FilledButton(
              onPressed: () => Navigator.of(context).popUntil((route) => route.isFirst),
              child: const Text('다음 검표'),
            ),
          ],
        ),
      ),
    );
  }
}
