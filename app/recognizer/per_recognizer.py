import os
import logging
from pathlib import Path
from typing import List, Optional, Tuple
import numpy as np
import onnxruntime as ort
from presidio_analyzer import EntityRecognizer, RecognizerResult
from transformers import AutoConfig, AutoTokenizer

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class KRPersonRecognizer(EntityRecognizer):
    """
    PER 엔티티 감지
    - Leo97/KoELECTRA-small-v3-modu-ner ONNX 모델 사용
    - Presidio ENTITY "KR_PERSON" 매핑
    """
    def __init__(self, model_dir: Optional[str] = None):
        super().__init__(supported_entities=["KR_PERSON"], supported_language="en")

        # 디렉토리와 ONNX 파일
        model_path = Path(os.getenv("KOELECTRA_ONNX_DIR", "/Users/skan/Desktop/Github/meritzfire-employee-pii/models/koelectra-onnx"))
        onnx_file = model_path / "model.onnx"
        
        # 토크나이저 로드
        self.tokenizer = AutoTokenizer.from_pretrained(
            str(model_path),
            use_fast=True,
            local_files_only=True,
        )

        # 라벨 맵핑 로드
        config = AutoConfig.from_pretrained(str(model_path), local_files_only=True)
        self.id2label = {int(i): label for i, label in config.id2label.items()}

        # ONNX 세션 초기화
        session_opts = ort.SessionOptions()
        session_opts.intra_op_num_threads = 1
        session_opts.inter_op_num_threads = 1
        session_opts.execution_mode = ort.ExecutionMode.ORT_PARALLEL
        
        self.session = ort.InferenceSession(
            str(onnx_file),
            sess_options=session_opts,
            providers=["CPUExecutionProvider"],
        )
        self.session_input_names = [inp.name for inp in self.session.get_inputs()]

        # Chunk & Window 설정
        max_length = getattr(self.tokenizer, "model_max_length", 512)
        if not isinstance(max_length, int) or max_length <= 0 or max_length > 8192:
            max_length = 512
        self.chunk_tokens = min(max_length, 512)
        self.overlap_tokens = min(64, self.chunk_tokens // 8)
        self.batch_size = 4
        
        logger.info(
            "KRPersonRecognizer initialized - chunk_tokens: %d, overlap_tokens: %d, batch_size: %d",
            self.chunk_tokens, self.overlap_tokens, self.batch_size
        )

    def __del__(self):
        """ONNX 세션 정리"""
        if hasattr(self, 'session'):
            try:
                del self.session
            except Exception:
                pass

    def load(self) -> None:
        """Presidio 호환성을 위한 빈 메서드"""
        pass

    def analyze(self, text: str, entities: List[str], nlp_artifacts=None) -> List[RecognizerResult]:
        if not text or "KR_PERSON" not in entities:
            return []

        chunks = self._chunk_by_tokens(text)
        if not chunks:
            return []

        # 배치 처리
        results: List[RecognizerResult] = []
        for i in range(0, len(chunks), self.batch_size):
            batch_slice = chunks[i : i + self.batch_size]
            batch_texts = [c[0] for c in batch_slice]
            batch_offsets = [c[1] for c in batch_slice]
            results.extend(self._run_batch(batch_texts, batch_offsets))

        # 결과 병합
        return self._merge_results(results)

    def _run_batch(self, texts: List[str], base_offsets: List[int]) -> List[RecognizerResult]:
        if not texts:
            return []

        # 토크나이징
        encoded = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=self.chunk_tokens,
            return_tensors="np",
            return_offsets_mapping=True,
        )

        offset_mapping = encoded.pop("offset_mapping")
        if isinstance(offset_mapping, np.ndarray):
            offset_batches = offset_mapping.tolist()
        else:
            offset_batches = offset_mapping

        # ONNX 추론
        ort_inputs = {
            name: encoded[name]
            for name in self.session_input_names
            if name in encoded
        }
        
        logits = self.session.run(None, ort_inputs)[0]
        probs = self._softmax(logits)
        pred_ids = probs.argmax(axis=-1)
        pred_scores = probs.max(axis=-1)

        # 엔티티 추출
        results: List[RecognizerResult] = []
        for idx, offsets in enumerate(offset_batches):
            base = base_offsets[idx]
            entities = self._gather_entities(
                base,
                offsets,
                pred_ids[idx],
                pred_scores[idx],
            )
            results.extend(entities)
        return results

    def _chunk_by_tokens(self, text: str) -> List[Tuple[str, int]]:
        if not text:
            return []

        # 전체 텍스트 토크나이징 (truncation 없이)
        encoding = self.tokenizer(
            text,
            add_special_tokens=False,
            return_offsets_mapping=True,
            truncation=False,
        )
        
        offsets = encoding.get("offset_mapping", [])
        if not offsets:
            return [(text, 0)]

        chunks: List[Tuple[str, int]] = []
        n_tokens = len(offsets)
        start_idx = 0
        
        while start_idx < n_tokens:
            end_idx = min(n_tokens, start_idx + self.chunk_tokens)
            
            # 실제 문자 위치 찾기
            start_char = self._window_start(offsets, start_idx, end_idx)
            end_char = self._window_end(offsets, start_idx, end_idx, len(text))

            if start_char is not None and end_char is not None and start_char < end_char:
                chunk_text = text[start_char:end_char]
                if chunk_text.strip():  # 공백만 있는 청크 제외
                    chunks.append((chunk_text, start_char))

            # 다음 청크로 이동
            if end_idx >= n_tokens:
                break
            start_idx = max(start_idx + 1, end_idx - self.overlap_tokens)

        return chunks or [(text, 0)]  # 청크가 없으면 전체 텍스트 반환

    def _gather_entities(
        self,
        base_offset: int,
        offsets: List[Tuple[int, int]],
        label_ids: np.ndarray,
        scores: np.ndarray,
    ) -> List[RecognizerResult]:
        entities: List[RecognizerResult] = []
        current = None

        for token_idx, (start_char, end_char) in enumerate(offsets):
            if end_char <= start_char:
                current = self._finalize_entity(current, entities)
                continue

            label_raw = self.id2label.get(int(label_ids[token_idx]), "O")
            prefix, entity = self._split_label(label_raw)
            
            if entity != "PS":  # PS = Person
                current = self._finalize_entity(current, entities)
                continue

            score = float(scores[token_idx])
            start = base_offset + start_char
            end = base_offset + end_char

            if prefix == "I" and current:
                # Continue current entity
                current["end"] = max(current["end"], end)
                current["scores"].append(score)
            else:
                # Start new entity
                current = self._finalize_entity(current, entities)
                current = {"start": start, "end": end, "scores": [score]}

        self._finalize_entity(current, entities)
        return entities

    def _merge_results(self, results: List[RecognizerResult]) -> List[RecognizerResult]:
        """중복된 결과 병합"""
        if not results:
            return []
            
        results.sort(key=lambda r: (r.start, r.end))
        merged: List[RecognizerResult] = []
        
        for r in results:
            if not merged or r.start > merged[-1].end:
                merged.append(r)
            else:
                # 겹치는 엔티티 병합
                merged[-1].end = max(merged[-1].end, r.end)
                merged[-1].score = max(merged[-1].score, r.score)
                
        return merged

    @staticmethod
    def _split_label(label: str) -> Tuple[str, str]:
        if "-" in label:
            return label.split("-", 1)
        return "B", label

    @staticmethod
    def _finalize_entity(current, entities: List[RecognizerResult]):
        if not current:
            return None
        avg_score = sum(current["scores"]) / len(current["scores"])
        entities.append(
            RecognizerResult(
                entity_type="KR_PERSON",
                start=current["start"],
                end=current["end"],
                score=avg_score,
            )
        )
        return None

    @staticmethod
    def _softmax(logits: np.ndarray) -> np.ndarray:
        exp = np.exp(logits - np.max(logits, axis=-1, keepdims=True))
        return exp / np.sum(exp, axis=-1, keepdims=True)

    @staticmethod
    def _window_start(
        offsets: List[Tuple[int, int]],
        start_idx: int,
        end_idx: int,
    ) -> Optional[int]:
        for idx in range(start_idx, min(end_idx, len(offsets))):
            start, end = offsets[idx]
            if end > start:
                return start
        return None

    @staticmethod
    def _window_end(
        offsets: List[Tuple[int, int]],
        start_idx: int,
        end_idx: int,
        text_length: int,
    ) -> Optional[int]:
        for idx in range(min(end_idx - 1, len(offsets) - 1), start_idx - 1, -1):
            start, end = offsets[idx]
            if end > start:
                return end
        return text_length if text_length > 0 else None
    

