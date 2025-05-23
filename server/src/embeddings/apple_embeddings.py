"""Apple-specific embeddings manager using CoreML and Neural Engine."""
import coremltools as ct
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import logging
from pathlib import Path
import platform
from sentence_transformers import SentenceTransformer
import torch
from .embeddings_manager import EmbeddingsManager
from transformers import AutoTokenizer
import json

logger = logging.getLogger(__name__)

class AppleEmbeddingsManager(EmbeddingsManager):
    """Manages text embeddings optimized for Apple Neural Engine."""
    
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        cache_dir: Optional[str] = None,
        compute_units: str = "ALL",  # ALL, CPU_AND_NE, CPU_ONLY
        max_length: int = 384
    ):
        """
        Initialize the Apple-optimized embeddings manager.
        
        Args:
            model_name: Name of the sentence-transformers model to use
            cache_dir: Directory to cache embeddings and models
            compute_units: CoreML compute units to use
            max_length: Maximum sequence length for tokenization
        """
        super().__init__(model_name=model_name, cache_dir=cache_dir, device="cpu")
        
        if not self._is_apple_silicon():
            logger.warning("Not running on Apple Silicon, falling back to CPU")
            return
        
        self.compute_units = compute_units
        self.max_length = max_length
        self.coreml_model = None
        self.tokenizer = None
        self.model_dir = Path(cache_dir) / "coreml_models" if cache_dir else None
        
        if self.model_dir:
            self.model_dir.mkdir(parents=True, exist_ok=True)
            
        # Set up tokenizer and model
        self._setup_tokenizer()
        self._setup_coreml_model()
    
    def _is_apple_silicon(self) -> bool:
        """Check if running on Apple Silicon."""
        return (
            platform.system() == "Darwin" and
            platform.processor() == "arm"
        )
    
    def _setup_tokenizer(self) -> None:
        """Set up the tokenizer for the model."""
        try:
            # Get the base model name from sentence-transformers
            base_model_name = self.model.get_config_dict()['modules'][0]['model_name']
            self.tokenizer = AutoTokenizer.from_pretrained(base_model_name)
            logger.info(f"Loaded tokenizer from {base_model_name}")
        except Exception as e:
            logger.error(f"Error setting up tokenizer: {str(e)}")
            self.tokenizer = None
    
    def _preprocess_text(self, text: str) -> Dict[str, np.ndarray]:
        """
        Preprocess text for CoreML model.
        
        Args:
            text: Input text to preprocess
            
        Returns:
            Dictionary of preprocessed inputs
        """
        if not self.tokenizer:
            raise RuntimeError("Tokenizer not initialized")
            
        # Tokenize with padding and truncation
        encoded = self.tokenizer(
            text,
            padding=True,
            truncation=True,
            max_length=self.max_length,
            return_tensors="np"
        )
        
        return {
            "input_ids": encoded["input_ids"],
            "attention_mask": encoded["attention_mask"],
            "token_type_ids": encoded.get("token_type_ids", np.zeros_like(encoded["input_ids"]))
        }
    
    def _setup_coreml_model(self) -> None:
        """Convert and load the CoreML model."""
        if not self._is_apple_silicon():
            return
            
        try:
            # Check if model already exists
            model_path = self._get_model_path()
            if model_path and model_path.exists():
                logger.info("Loading existing CoreML model")
                self.coreml_model = ct.models.MLModel(str(model_path))
                return
            
            logger.info("Converting model to CoreML format")
            
            # Create sample inputs for tracing
            sample_text = "This is a sample text for tracing"
            sample_inputs = self._preprocess_text(sample_text)
            
            # Trace the PyTorch model
            def trace_model(inputs):
                return self.model.encode(
                    inputs,
                    convert_to_numpy=True,
                    normalize_embeddings=True
                )
            
            traced_model = torch.jit.trace(
                trace_model,
                (sample_inputs,),
                strict=False
            )
            
            # Convert to CoreML with proper input types
            input_specs = [
                ct.TensorType(
                    name="input_ids",
                    shape=(1, self.max_length),
                    dtype=np.int32
                ),
                ct.TensorType(
                    name="attention_mask",
                    shape=(1, self.max_length),
                    dtype=np.int32
                ),
                ct.TensorType(
                    name="token_type_ids",
                    shape=(1, self.max_length),
                    dtype=np.int32
                )
            ]
            
            coreml_model = ct.convert(
                traced_model,
                inputs=input_specs,
                compute_units=self.compute_units,
                minimum_deployment_target=ct.target.macOS13,
                compute_precision=ct.precision.FLOAT16  # Use FP16 for better performance
            )
            
            # Save model metadata
            metadata = {
                "max_length": self.max_length,
                "model_name": self.model.get_model_name(),
                "compute_units": self.compute_units
            }
            
            if model_path:
                # Save the model and metadata
                metadata_path = model_path.with_suffix(".json")
                with open(metadata_path, "w") as f:
                    json.dump(metadata, f)
                coreml_model.save(str(model_path))
            
            self.coreml_model = coreml_model
            logger.info("Successfully converted and loaded CoreML model")
            
        except Exception as e:
            logger.error(f"Error setting up CoreML model: {str(e)}")
            logger.warning("Falling back to CPU processing")
    
    def _get_model_path(self) -> Optional[Path]:
        """Get path for the CoreML model."""
        if not self.model_dir:
            return None
            
        model_name = self.model.get_model_name()
        safe_name = "".join(c if c.isalnum() else "_" for c in model_name)
        return self.model_dir / f"{safe_name}.mlmodel"
    
    def get_embeddings(
        self,
        chunks: List[Any],
        use_cache: bool = True,
        batch_size: int = 32
    ) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        """
        Get embeddings using CoreML when available.
        
        Args:
            chunks: List of text chunks to embed
            use_cache: Whether to use cached embeddings
            batch_size: Batch size for embedding generation
            
        Returns:
            Tuple of (embeddings array, chunk metadata list)
        """
        if not self.coreml_model or not self._is_apple_silicon():
            return super().get_embeddings(chunks, use_cache, batch_size)
        
        if not chunks:
            return np.array([]), []
        
        embeddings = []
        metadata_list = []
        texts_to_embed = []
        cache_keys = []
        
        # Check cache and collect texts that need embedding
        for chunk in chunks:
            cache_key = self._get_cache_key(chunk)
            cached_embedding = self._load_from_cache(cache_key) if use_cache else None
            
            if cached_embedding is not None:
                embeddings.append(cached_embedding)
                metadata_list.append(chunk.metadata)
            else:
                texts_to_embed.append(chunk.content)
                cache_keys.append(cache_key)
                metadata_list.append(chunk.metadata)
        
        # Generate new embeddings for uncached texts
        if texts_to_embed:
            new_embeddings = []
            
            # Process in batches
            for i in range(0, len(texts_to_embed), batch_size):
                batch_texts = texts_to_embed[i:i + batch_size]
                
                try:
                    # Preprocess batch
                    batch_inputs = [self._preprocess_text(text) for text in batch_texts]
                    
                    # Get embeddings using CoreML
                    batch_predictions = []
                    for inputs in batch_inputs:
                        prediction = self.coreml_model.predict(inputs)
                        embedding = prediction["output"]
                        # Normalize embedding
                        embedding = embedding / np.linalg.norm(embedding)
                        batch_predictions.append(embedding)
                    
                    new_embeddings.extend(batch_predictions)
                    
                except Exception as e:
                    logger.error(f"CoreML prediction error: {str(e)}")
                    # Fall back to CPU if CoreML fails
                    batch_embeddings = self.model.encode(
                        batch_texts,
                        convert_to_numpy=True,
                        normalize_embeddings=True,
                        show_progress_bar=False
                    )
                    new_embeddings.extend(batch_embeddings)
            
            # Cache new embeddings
            if use_cache:
                for i, cache_key in enumerate(cache_keys):
                    self._save_to_cache(cache_key, new_embeddings[i])
            
            embeddings.extend(new_embeddings)
        
        return np.array(embeddings), metadata_list
    
    def search(
        self,
        query: str,
        embeddings: np.ndarray,
        metadata: List[Dict[str, Any]],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for most relevant chunks using CoreML when available.
        
        Args:
            query: Search query
            embeddings: Array of chunk embeddings
            metadata: List of chunk metadata
            top_k: Number of results to return
            
        Returns:
            List of results with metadata and similarity scores
        """
        if not self.coreml_model or not self._is_apple_silicon():
            return super().search(query, embeddings, metadata, top_k)
        
        if len(embeddings) == 0:
            return []
        
        try:
            # Preprocess query
            query_inputs = self._preprocess_text(query)
            
            # Generate query embedding using CoreML
            query_prediction = self.coreml_model.predict(query_inputs)
            query_embedding = query_prediction["output"]
            
            # Normalize query embedding
            query_embedding = query_embedding / np.linalg.norm(query_embedding)
            
            # Calculate similarities on CPU (small operation)
            similarities = np.dot(embeddings, query_embedding)
            
            # Get top k results
            top_indices = np.argsort(similarities)[-top_k:][::-1]
            
            results = []
            for idx in top_indices:
                results.append({
                    **metadata[idx],
                    'similarity': float(similarities[idx])
                })
            
            return results
            
        except Exception as e:
            logger.error(f"CoreML search error: {str(e)}")
            return super().search(query, embeddings, metadata, top_k) 