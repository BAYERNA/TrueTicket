import 'dart:io';

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';

import '../services/verification_api.dart';
import 'result_screen.dart';

enum _CaptureStep { live, reference }

/// SCR-06 두 번째 단계: 입장자 얼굴과 신분증을 순서대로 촬영해 verification-service로 전송한다
/// (FR-011 YOLOv8 얼굴 검출 + 신분증 대조).
class CaptureScreen extends StatefulWidget {
  const CaptureScreen({super.key, required this.qrCode});

  final String qrCode;

  @override
  State<CaptureScreen> createState() => _CaptureScreenState();
}

class _CaptureScreenState extends State<CaptureScreen> {
  CameraController? _cameraController;
  _CaptureStep _step = _CaptureStep.live;
  File? _liveImage;
  File? _referenceImage;
  bool _submitting = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _initCamera();
  }

  Future<void> _initCamera() async {
    final cameras = await availableCameras();
    final frontCamera = cameras.firstWhere(
      (camera) => camera.lensDirection == CameraLensDirection.front,
      orElse: () => cameras.first,
    );
    final controller = CameraController(
      frontCamera,
      ResolutionPreset.medium,
      enableAudio: false,
    );
    await controller.initialize();
    if (!mounted) return;
    setState(() => _cameraController = controller);
  }

  @override
  void dispose() {
    _cameraController?.dispose();
    super.dispose();
  }

  Future<void> _capture() async {
    final controller = _cameraController;
    if (controller == null || !controller.value.isInitialized) return;

    final file = await controller.takePicture();

    setState(() {
      if (_step == _CaptureStep.live) {
        _liveImage = File(file.path);
        _step = _CaptureStep.reference;
      } else {
        _referenceImage = File(file.path);
      }
    });

    if (_referenceImage != null) {
      await _submit();
    }
  }

  Future<void> _submit() async {
    final liveImage = _liveImage;
    final referenceImage = _referenceImage;
    if (liveImage == null || referenceImage == null) return;

    setState(() {
      _submitting = true;
      _errorMessage = null;
    });

    try {
      final result = await VerificationApi().verify(
        qrCode: widget.qrCode,
        verifiedBy: 'gate-staff', // TODO: 스태프 로그인이 붙으면 실제 스태프 ID로 교체한다.
        liveImage: liveImage,
        referenceImage: referenceImage,
      );
      if (!mounted) return;
      await Navigator.of(context).pushReplacement<void, void>(
        MaterialPageRoute(builder: (_) => ResultScreen(result: result)),
      );
    } on VerificationApiException catch (e) {
      _resetAfterError(e.message);
    } catch (e) {
      _resetAfterError('알 수 없는 오류가 발생했습니다: $e');
    }
  }

  void _resetAfterError(String message) {
    if (!mounted) return;
    setState(() {
      _errorMessage = message;
      _submitting = false;
      _step = _CaptureStep.live;
      _liveImage = null;
      _referenceImage = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    final controller = _cameraController;

    return Scaffold(
      appBar: AppBar(
        title: Text(_step == _CaptureStep.live ? '입장자 얼굴 촬영' : '신분증 촬영'),
      ),
      body: controller == null || !controller.value.isInitialized
          ? const Center(child: CircularProgressIndicator())
          : Stack(
              fit: StackFit.expand,
              children: [
                CameraPreview(controller),
                if (_errorMessage != null)
                  Align(
                    alignment: Alignment.topCenter,
                    child: Container(
                      margin: const EdgeInsets.all(16),
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.red.shade700,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        _errorMessage!,
                        style: const TextStyle(color: Colors.white),
                      ),
                    ),
                  ),
                Align(
                  alignment: Alignment.bottomCenter,
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: _submitting
                        ? const CircularProgressIndicator(color: Colors.white)
                        : FloatingActionButton.large(
                            onPressed: _capture,
                            child: const Icon(Icons.camera_alt),
                          ),
                  ),
                ),
              ],
            ),
    );
  }
}
