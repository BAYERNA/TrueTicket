import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import 'capture_screen.dart';

/// SCR-06 첫 단계: QR 티켓 스캔 (FR-010).
class ScanScreen extends StatefulWidget {
  const ScanScreen({super.key, required this.accessToken});

  final String accessToken;

  @override
  State<ScanScreen> createState() => _ScanScreenState();
}

class _ScanScreenState extends State<ScanScreen> {
  final MobileScannerController _controller = MobileScannerController();
  bool _handledDetection = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _onDetect(BarcodeCapture capture) {
    if (_handledDetection) return;

    final qrCode = capture.barcodes.firstOrNull?.rawValue;
    if (qrCode == null || qrCode.isEmpty) return;

    setState(() => _handledDetection = true);
    _controller.stop();

    Navigator.of(context)
        .push<void>(
          MaterialPageRoute(builder: (_) => CaptureScreen(qrCode: qrCode, accessToken: widget.accessToken)),
        )
        .then((_) {
          if (!mounted) return;
          setState(() => _handledDetection = false);
          _controller.start();
        });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('현장 검표')),
      body: Stack(
        fit: StackFit.expand,
        children: [
          MobileScanner(controller: _controller, onDetect: _onDetect),
          Align(
            alignment: Alignment.bottomCenter,
            child: Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(vertical: 24),
              color: Colors.black54,
              child: const Text(
                '입장권 QR 코드를 화면 중앙에 맞춰주세요',
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.white, fontSize: 16),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

extension _FirstOrNull<T> on List<T> {
  T? get firstOrNull => isEmpty ? null : first;
}
