#!/usr/bin/env python3
"""
Treina modelo de Matching Semântico fine-tuned
Usa pares anotados (currículo, vaga, score) para melhorar Sentence-BERT
"""
import json
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer, InputExample, losses, evaluation
from torch.utils.data import DataLoader
import torch


def load_annotated_data(file_path: str):
    """Carrega dados anotados"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Filtrar apenas pares com anotação
    annotated = [
        pair for pair in data 
        if pair.get('match_score') is not None
    ]
    
    return annotated


def prepare_training_data(annotated_pairs):
    """Prepara dados para treinamento"""
    print("\n🔧 Preparando dados de treinamento...")
    
    train_examples = []
    
    for pair in annotated_pairs:
        # Combinar informações do currículo
        resume_text = pair['resume_text']
        resume_skills = ", ".join(pair.get('resume_skills', []))
        resume_full = f"{resume_text}\nHabilidades: {resume_skills}"
        
        # Texto da vaga
        job_text = f"{pair['job_title']}\n{pair['job_description']}"
        
        # Score (0-1)
        score = float(pair['match_score'])
        
        # Criar exemplo para treinamento
        example = InputExample(
            texts=[resume_full, job_text],
            label=score
        )
        train_examples.append(example)
    
    print(f"✅ Preparados {len(train_examples)} exemplos de treinamento")
    
    return train_examples


def train_semantic_matcher(
    annotated_file: str = "data/matching_pairs_annotated.json",
    model_name: str = "paraphrase-multilingual-mpnet-base-v2",
    output_path: str = "models/semantic_matcher_finetuned",
    epochs: int = 3,
    batch_size: int = 16
):
    """
    Treina modelo de matching semântico
    
    Args:
        annotated_file: Arquivo JSON com pares anotados
        model_name: Modelo base do Sentence-BERT
        output_path: Onde salvar modelo treinado
        epochs: Número de épocas
        batch_size: Tamanho do batch
    """
    print("=" * 80)
    print("🚀 TREINAMENTO DE MODELO DE MATCHING SEMÂNTICO")
    print("=" * 80)
    
    # 1. Carregar dados
    print(f"\n📥 Carregando dados de {annotated_file}...")
    annotated_pairs = load_annotated_data(annotated_file)
    
    if len(annotated_pairs) < 10:
        print(f"❌ Dados insuficientes! Encontrados apenas {len(annotated_pairs)} pares anotados.")
        print(f"   Recomendado: 100-300 pares anotados")
        return
    
    print(f"✅ Carregados {len(annotated_pairs)} pares anotados")
    
    # Estatísticas
    scores = [p['match_score'] for p in annotated_pairs]
    print(f"\n📊 Distribuição de scores:")
    print(f"   Média: {np.mean(scores):.3f}")
    print(f"   Min-Max: {min(scores):.3f} - {max(scores):.3f}")
    print(f"   Desvio: {np.std(scores):.3f}")
    
    # 2. Preparar dados
    train_examples = prepare_training_data(annotated_pairs)
    
    # Split train/validation (80/20)
    split_idx = int(len(train_examples) * 0.8)
    train_data = train_examples[:split_idx]
    val_data = train_examples[split_idx:]
    
    print(f"\n📦 Split dos dados:")
    print(f"   Treino: {len(train_data)} exemplos")
    print(f"   Validação: {len(val_data)} exemplos")
    
    # 3. Carregar modelo base
    print(f"\n🤖 Carregando modelo base: {model_name}...")
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    model = SentenceTransformer(model_name, device=device)
    print(f"✅ Modelo carregado em: {device}")
    
    # 4. Preparar DataLoader com batch size maior para dataset grande
    effective_batch_size = min(batch_size * 2, 32) if len(train_data) > 1000 else batch_size
    
    train_dataloader = DataLoader(
        train_data,
        shuffle=True,
        batch_size=effective_batch_size
    )
    
    # 5. Loss function (Cosine Similarity)
    train_loss = losses.CosineSimilarityLoss(model)
    
    print(f"\n⚙️  Configuração:")
    print(f"   Batch size: {effective_batch_size}")
    print(f"   Steps por época: {len(train_dataloader)}")
    print(f"   Total steps: {len(train_dataloader) * epochs}")
    
    # 6. Evaluator (opcional, para monitorar progresso)
    if len(val_data) > 0:
        val_sentences1 = [ex.texts[0] for ex in val_data]
        val_sentences2 = [ex.texts[1] for ex in val_data]
        val_scores = [ex.label for ex in val_data]
        
        evaluator = evaluation.EmbeddingSimilarityEvaluator(
            val_sentences1,
            val_sentences2,
            val_scores,
            name='validation'
        )
    else:
        evaluator = None
    
    # 7. Treinar
    print(f"\n🏋️ Treinando por {epochs} épocas...")
    warmup_steps = int(len(train_dataloader) * epochs * 0.1)  # 10% warmup
    
    model.fit(
        train_objectives=[(train_dataloader, train_loss)],
        epochs=epochs,
        warmup_steps=warmup_steps,
        evaluator=evaluator,
        evaluation_steps=len(train_dataloader) // 2,  # Avaliar 2x por época
        output_path=output_path,
        save_best_model=True,
        show_progress_bar=True
    )
    
    print(f"\n✅ Treinamento concluído!")
    print(f"💾 Modelo salvo em: {output_path}")
    
    # 8. Teste final
    print(f"\n🔬 Testando modelo...")
    
    # Pegar alguns exemplos de validação
    test_pairs = val_data[:5] if len(val_data) >= 5 else val_data
    
    for i, example in enumerate(test_pairs, 1):
        resume_text = example.texts[0][:200] + "..."  # Primeiros 200 chars
        job_text = example.texts[1][:150] + "..."
        true_score = example.label
        
        # Calcular similarity com modelo treinado
        embeddings = model.encode([example.texts[0], example.texts[1]])
        pred_score = float(np.dot(embeddings[0], embeddings[1]) / 
                          (np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])))
        
        print(f"\n[{i}] Resumo: {resume_text}")
        print(f"    Vaga: {job_text}")
        print(f"    Score Real: {true_score:.3f} | Predito: {pred_score:.3f} | "
              f"Erro: {abs(true_score - pred_score):.3f}")
    
    print("\n" + "=" * 80)
    print("✅ TREINAMENTO FINALIZADO!")
    print("=" * 80)
    print(f"\n💡 Para usar o modelo:")
    print(f"   from sentence_transformers import SentenceTransformer")
    print(f"   model = SentenceTransformer('{output_path}')")
    print(f"   embeddings = model.encode([resume_text, job_text])")
    print(f"   similarity = cosine_similarity(embeddings[0], embeddings[1])")
    
    print(f"\n📝 Próximo passo:")
    print(f"   Atualizar app/ml/semantic_similarity.py para usar o novo modelo")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Treina modelo de matching semântico')
    parser.add_argument('--data', type=str, default='data/matching_pairs_annotated.json',
                       help='Arquivo com dados anotados')
    parser.add_argument('--model', type=str, default='paraphrase-multilingual-mpnet-base-v2',
                       help='Modelo base do Sentence-BERT')
    parser.add_argument('--output', type=str, default='models/semantic_matcher_finetuned',
                       help='Diretório de saída')
    parser.add_argument('--epochs', type=int, default=3,
                       help='Número de épocas')
    parser.add_argument('--batch-size', type=int, default=16,
                       help='Tamanho do batch')
    
    args = parser.parse_args()
    
    train_semantic_matcher(
        annotated_file=args.data,
        model_name=args.model,
        output_path=args.output,
        epochs=args.epochs,
        batch_size=args.batch_size
    )
