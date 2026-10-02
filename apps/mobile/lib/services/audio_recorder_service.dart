import 'dart:async';
import 'dart:typed_data';

import 'package:record/record.dart';

/// AUDIO CONTRACT (mandatory):
/// - Format: 16-bit signed little-endian PCM
/// - Channels: Mono
/// - Sample Rate: 16000 Hz
/// - No other format is accepted by the translation pipeline
/// AUDIO CONTRACT: 16kHz mono PCM16 only
class AudioRecorderService {
  AudioRecorderService({AudioRecorder? recorder})
      : _recorder = recorder ?? AudioRecorder();

  static const int sampleRate = 16000;
  static const int channels = 1;
  static const int _fallbackSampleRate = 48000;

  final AudioRecorder _recorder;
  final StreamController<Uint8List> _pcm16Chunks =
      StreamController<Uint8List>.broadcast();
  StreamSubscription<Uint8List>? _recordingSubscription;

  /// Raw PCM16, 16 kHz mono chunks safe to send over WebSocket or HTTP.
  Stream<Uint8List> get pcm16Chunks => _pcm16Chunks.stream;

  Future<void> start() async {
    if (!await _recorder.hasPermission()) {
      throw StateError('Microphone permission was not granted');
    }

    try {
      await _startStream(sampleRate);
    } catch (_) {
      // Some devices reject 16 kHz capture; use a known PCM capture rate and
      // resample its mono PCM16 stream before it leaves this service.
      await _startStream(_fallbackSampleRate);
    }
  }

  Future<void> stop() async {
    await _recordingSubscription?.cancel();
    _recordingSubscription = null;
    await _recorder.stop();
  }

  Future<void> dispose() async {
    await stop();
    await _pcm16Chunks.close();
    await _recorder.dispose();
  }

  Future<void> _startStream(int sourceSampleRate) async {
    final stream = await _recorder.startStream(
      RecordConfig(
        encoder: AudioEncoder.pcm16bits,
        numChannels: channels,
        sampleRate: sourceSampleRate,
      ),
    );
    _recordingSubscription = stream.listen(
      (chunk) => _pcm16Chunks.add(
        sourceSampleRate == sampleRate
            ? chunk
            : _resamplePcm16Mono(chunk, sourceSampleRate),
      ),
      onError: _pcm16Chunks.addError,
    );
  }

  static Uint8List _resamplePcm16Mono(Uint8List input, int sourceSampleRate) {
    if (input.lengthInBytes.isOdd) {
      throw const FormatException('PCM16 chunks must contain complete samples');
    }
    if (input.isEmpty) {
      return input;
    }
    if (sourceSampleRate == sampleRate) {
      return input;
    }

    final sourceSamples = input.lengthInBytes ~/ 2;
    final targetSamples = (sourceSamples * sampleRate / sourceSampleRate)
        .round()
        .clamp(1, 1 << 31);
    final output = Uint8List(targetSamples * 2);
    final source = ByteData.sublistView(input);
    final target = ByteData.sublistView(output);

    for (var targetIndex = 0; targetIndex < targetSamples; targetIndex++) {
      final position = targetIndex * sourceSampleRate;
      final lowerIndex = (position ~/ sampleRate).clamp(0, sourceSamples - 1);
      final upperIndex = (lowerIndex + 1).clamp(0, sourceSamples - 1);
      final fraction = position % sampleRate;
      final lower = source.getInt16(lowerIndex * 2, Endian.little);
      final upper = source.getInt16(upperIndex * 2, Endian.little);
      final value = lower + ((upper - lower) * fraction ~/ sampleRate);
      target.setInt16(targetIndex * 2, value, Endian.little);
    }
    return output;
  }
}
