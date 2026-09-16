# verification-app

현장 검표 스태프용 Flutter 앱 (SCR-06). QR 스캔 → 입장자 얼굴 촬영 → 신분증 촬영 →
verification-service 호출 → 입장 승인/거부 표시 순서로 동작한다.

## 초기 설정

이 디렉토리는 `lib/`와 `pubspec.yaml`만 있는 소스 스캐폴드다. 이 세션에는 Flutter SDK가
설치되어 있지 않아 `android/`, `ios/` 등 플랫폼 프로젝트 파일을 생성하지 못했다.
로컬에서 다음을 실행해 플랫폼 스캐폴딩을 채워 넣는다.

```bash
flutter create --project-name verification_app --org com.trueticket .
flutter pub get
flutter analyze
flutter run
```

`flutter create .`는 기존 `lib/main.dart`, `pubspec.yaml`을 덮어쓰지 않고 누락된
`android/`, `ios/` 등만 채워 넣는다(플랫폼 폴더가 비어 있는 경우).

## 구조

```
lib/
├── main.dart                 앱 진입점
├── screens/
│   ├── scan_screen.dart       1단계: QR 스캔 (mobile_scanner)
│   ├── capture_screen.dart    2단계: 얼굴/신분증 촬영 (camera)
│   └── result_screen.dart     3단계: 매칭 결과·입장 승인/거부 표시
├── services/
│   └── verification_api.dart  verification-service REST 클라이언트 (multipart)
└── models/
    └── verification_result.dart
```

## 설정

`lib/services/verification_api.dart`의 `baseUrl` 기본값은 `http://localhost:8093`
(verification-service 직접 호출)이다. 실기기에서 테스트할 때는 PC의 LAN IP로,
배포 환경에서는 Gateway 주소로 교체한다.

## 참고

- 카메라/QR 스캔 권한(`Info.plist`의 `NSCameraUsageDescription`, Android
  `AndroidManifest.xml`의 `CAMERA` 권한)은 `flutter create` 이후 플랫폼 설정 파일에
  직접 추가해야 한다.
- 이 코드는 Flutter SDK 없이 작성되어 `flutter analyze`로 검증되지 않았다. 위 초기
  설정을 마친 뒤 가장 먼저 `flutter analyze`를 실행해 확인한다.
