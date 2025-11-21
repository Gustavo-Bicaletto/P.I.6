#!/usr/bin/env python3
"""
Treinamento avançado com data augmentation e validação cruzada
"""
import sys
import json
import numpy as np
from pathlib import Path
from sklearn.model_selection import KFold
import torch

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sentence_transformers import SentenceTransformer, InputExample, losses, evaluation
from torch.utils.data import DataLoader


def load_and_augment_data(filepath: str):
    """Carrega dados e aplica data augmentation"""
    print(f"\n📥 Carregando dados de {filepath}...")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        pairs = json.load(f)
    
    # Filtrar apenas pares anotados
    pairs = [p for p in pairs if p.get('match_score') is not None]
    print(f"✅ {len(pairs)} pares anotados")
    
    # Preparar exemplos
    examples = []
    for pair in pairs:
        resume_text = pair['resume_text']
        job_text = pair['job_description']
        score = float(pair['match_score'])
        
        # Exemplo original
        examples.append(InputExample(texts=[resume_text, job_text], label=score))
        
        # Data augmentation: inverter ordem (simetria)
        examples.append(InputExample(texts=[job_text, resume_text], label=score))
    
    print(f"✅ {len(examples)} exemplos (com augmentation)")
    return examples


def train_with_cross_validation(examples, n_splits=5, epochs=10):
    """Treina modelo com validação cruzada"""
    
    print(f"\n🔄 Treinamento com {n_splits}-fold Cross Validation")
    print("=" * 80)
    
    kf = KFold(n_splits=n_splits, shuffle=True, random_state=42)
    fold_scores = []
    
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    
    for fold, (train_idx, val_idx) in enumerate(kf.split(examples), 1):
        print(f"\n📊 Fold {fold}/{n_splits}")
        print("-" * 80)
        
        # Split dados
        train_examples = [examples[i] for i in train_idx]
        val_examples = [examples[i] for i in val_idx]
        
        print(f"Treino: {len(train_examples)} | Validação: {len(val_examples)}")
        
        # Carregar modelo base
        model = SentenceTransformer('paraphrase-multilingual-mpnet-base-v2', device=device)
        
        # Preparar DataLoader
        train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=32)
        
        # Loss function
        train_loss = losses.CosineSimilarityLoss(model)
        
        # Evaluator
        val_sentences1 = [ex.texts[0] for ex in val_examples]
        val_sentences2 = [ex.texts[1] for ex in val_examples]
        val_scores = [ex.label for ex in val_examples]
        
        evaluator = evaluation.EmbeddingSimilarityEvaluator(
            val_sentences1,
            val_sentences2,
            val_scores,
            name=f'fold{fold}_validation'
        )
        
        # Treinar
        warmup_steps = int(len(train_dataloader) * epochs * 0.1)
        
        model.fit(
            train_objectives=[(train_dataloader, train_loss)],
            epochs=epochs,
            warmup_steps=warmup_steps,
            evaluator=evaluator,
            evaluation_steps=len(train_dataloader) // 2,
            output_path=f'models/semantic_matcher_fold{fold}',
            save_best_model=True,
            show_progress_bar=True
        )
        
        # Avaliar no fold
        score = evaluator(model)
        fold_scores.append(score)
        print(f"\n✅ Fold {fold} - Pearson: {score:.4f}")
    
    # Resultados finais
    print("\n" + "=" * 80)
    print("📊 RESULTADOS DA VALIDAÇÃO CRUZADA")
    print("=" * 80)
    
    for i, score in enumerate(fold_scores, 1):
        print(f"Fold {i}: Pearson = {score:.4f}")
    
    mean_score = np.mean(fold_scores)
    std_score = np.std(fold_scores)
    
    print(f"\n📈 Média: {mean_score:.4f} ± {std_score:.4f}")
    print(f"📈 Melhor: {max(fold_scores):.4f}")
    print(f"📈 Pior: {min(fold_scores):.4f}")
    
    return fold_scores


def train_final_model(examples, epochs=12, output_path='models/semantic_matcher_finetuned'):
    """Treina modelo final com todos os dados"""
    
    print("\n" + "=" * 80)
    print("🚀 TREINAMENTO DO MODELO FINAL")
    print("=" * 80)
    
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    
    # Split 90/10 para validação final
    split_idx = int(len(examples) * 0.9)
    train_examples = examples[:split_idx]
    val_examples = examples[split_idx:]
    
    print(f"\n📦 Treino: {len(train_examples)} | Validação: {len(val_examples)}")
    
    # Carregar modelo base
    print(f"\n🤖 Carregando modelo base...")
    model = SentenceTransformer('paraphrase-multilingual-mpnet-base-v2', device=device)
    print(f"✅ Modelo carregado em: {device}")
    
    # Preparar DataLoader com batch maior
    train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=32)
    
    # Loss function
    train_loss = losses.CosineSimilarityLoss(model)
    
    # Evaluator
    val_sentences1 = [ex.texts[0] for ex in val_examples]
    val_sentences2 = [ex.texts[1] for ex in val_examples]
    val_scores = [ex.label for ex in val_examples]
    
    evaluator = evaluation.EmbeddingSimilarityEvaluator(
        val_sentences1,
        val_sentences2,
        val_scores,
        name='final_validation'
    )
    
    print(f"\n⚙️  Configuração:")
    print(f"   Batch size: 32")
    print(f"   Épocas: {epochs}")
    print(f"   Steps por época: {len(train_dataloader)}")
    print(f"   Total steps: {len(train_dataloader) * epochs}")
    
    # Treinar
    warmup_steps = int(len(train_dataloader) * epochs * 0.1)
    print(f"   Warmup steps: {warmup_steps}")
    
    print(f"\n🏋️ Treinando por {epochs} épocas...")
    
    model.fit(
        train_objectives=[(train_dataloader, train_loss)],
        epochs=epochs,
        warmup_steps=warmup_steps,
        evaluator=evaluator,
        evaluation_steps=len(train_dataloader) // 2,
        output_path=output_path,
        save_best_model=True,
        show_progress_bar=True
    )
    
    print(f"\n✅ Modelo final salvo em: {output_path}")
    
    # Avaliar modelo final
    final_score = evaluator(model)
    print(f"\n📊 Score Final de Validação: Pearson = {final_score:.4f}")
    
    return final_score


def main():
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=str, default='data/matching_pairs_annotated.json')
    parser.add_argument('--cv', action='store_true', help='Realizar validação cruzada')
    parser.add_argument('--cv-folds', type=int, default=5, help='Número de folds')
    parser.add_argument('--cv-epochs', type=int, default=8, help='Épocas por fold')
    parser.add_argument('--final-epochs', type=int, default=12, help='Épocas do modelo final')
    parser.add_argument('--output', type=str, default='models/semantic_matcher_finetuned')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("🚀 TREINAMENTO AVANÇADO - MODELO DE MATCHING SEMÂNTICO")
    print("=" * 80)
    
    # Carregar e aumentar dados
    examples = load_and_augment_data(args.data)
    
    # Validação cruzada (opcional)
    if args.cv:
        cv_scores = train_with_cross_validation(
            examples, 
            n_splits=args.cv_folds, 
            epochs=args.cv_epochs
        )
    
    # Treinar modelo final
    final_score = train_final_model(
        examples, 
        epochs=args.final_epochs,
        output_path=args.output
    )
    
    print("\n" + "=" * 80)
    print("✅ TREINAMENTO COMPLETO!")
    print("=" * 80)
    
    if args.cv:
        print(f"\n📊 Validação Cruzada: {np.mean(cv_scores):.4f} ± {np.std(cv_scores):.4f}")
    
    print(f"📊 Modelo Final: Pearson = {final_score:.4f}")
    print(f"\n💾 Modelo salvo em: {args.output}")
    print("\n🎯 Próximo passo:")
    print(f"   python app/ml/evaluate_semantic_matcher.py --model {args.output}")


if __name__ == "__main__":
    main()
