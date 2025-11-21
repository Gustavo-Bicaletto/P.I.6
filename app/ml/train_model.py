#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Treina modelo de classificação de currículos usando Transformers.
"""
import os
import json
import torch
from datetime import datetime
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
    EarlyStoppingCallback
)
from datasets import Dataset
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
import numpy as np


def load_dataset(filepath: str):
    """Carrega dataset JSON"""
    print(f"   📂 Carregando {filepath}...")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return Dataset.from_list(data)


def compute_metrics(pred):
    """Calcula métricas de avaliação"""
    labels = pred.label_ids
    preds = pred.predictions.argmax(-1)
    
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, preds, average='binary'
    )
    acc = accuracy_score(labels, preds)
    cm = confusion_matrix(labels, preds)
    
    return {
        'accuracy': acc,
        'f1': f1,
        'precision': precision,
        'recall': recall,
    }


def train_resume_classifier(
    data_dir: str = "data/training",
    model_name: str = "distilbert-base-uncased",
    output_dir: str = "models/resume_classifier",
    max_length: int = 512,
    batch_size: int = 16,
    num_epochs: int = 3,
    learning_rate: float = 2e-5,
    use_gpu: bool = True
):
    """
    Treina classificador de currículos.
    
    Args:
        data_dir: Diretório com train/val/test.json
        model_name: Nome do modelo HuggingFace (distilbert, roberta, etc)
        output_dir: Onde salvar o modelo treinado
        max_length: Tamanho máximo do texto tokenizado
        batch_size: Tamanho do batch
        num_epochs: Número de épocas
        learning_rate: Taxa de aprendizado
        use_gpu: Usar GPU se disponível
    """
    print(f"🚀 Iniciando treinamento com {model_name}")
    
    # Verificar GPU
    device = "cuda" if use_gpu and torch.cuda.is_available() else "cpu"
    print(f"   Device: {device}")
    if device == "cuda":
        print(f"   GPU: {torch.cuda.get_device_name(0)}")
    
    # Carregar tokenizer e modelo
    print(f"\n📥 Carregando tokenizer e modelo base...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=2  
    )
    
    # Carregar datasets
    print(f"\n📂 Carregando datasets de {data_dir}...")
    train_dataset = load_dataset(os.path.join(data_dir, "train.json"))
    val_dataset = load_dataset(os.path.join(data_dir, "validation.json"))
    test_dataset = load_dataset(os.path.join(data_dir, "test.json"))
    
    print(f"\n📊 Datasets carregados:")
    print(f"   Treino: {len(train_dataset)} amostras")
    print(f"   Validação: {len(val_dataset)} amostras")
    print(f"   Teste: {len(test_dataset)} amostras")
    
    # Tokenizar datasets
    print(f"\n🔤 Tokenizando textos (max_length={max_length})...")
    
    def tokenize_function(examples):
        return tokenizer(
            examples["text"],
            padding="max_length",
            truncation=True,
            max_length=max_length
        )
    
    train_dataset = train_dataset.map(tokenize_function, batched=True)
    val_dataset = val_dataset.map(tokenize_function, batched=True)
    test_dataset = test_dataset.map(tokenize_function, batched=True)
    
    print("   ✅ Tokenização concluída")
    
    # Preparar para PyTorch
    train_dataset = train_dataset.rename_column("label", "labels")
    val_dataset = val_dataset.rename_column("label", "labels")
    test_dataset = test_dataset.rename_column("label", "labels")
    
    train_dataset.set_format("torch", columns=["input_ids", "attention_mask", "labels"])
    val_dataset.set_format("torch", columns=["input_ids", "attention_mask", "labels"])
    test_dataset.set_format("torch", columns=["input_ids", "attention_mask", "labels"])
    
    # Configurar treinamento
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=num_epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        learning_rate=learning_rate,
        weight_decay=0.01,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        push_to_hub=False,
        logging_dir=f"{output_dir}/logs",
        logging_steps=50,
        save_total_limit=2,
        fp16=use_gpu and torch.cuda.is_available(),  # Mixed precision se GPU disponível
    )
    
    # Criar Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=2)]
    )
    
    # Treinar
    print(f"\n🏋️  Iniciando treinamento...")
    print(f"   Épocas: {num_epochs}")
    print(f"   Batch size: {batch_size}")
    print(f"   Learning rate: {learning_rate}")
    print(f"   Total steps: ~{(len(train_dataset) // batch_size) * num_epochs}")
    print("\n" + "="*80)
    
    train_result = trainer.train()
    
    print("\n" + "="*80)
    print("✅ Treinamento concluído!")
    
    # Salvar modelo
    print(f"\n💾 Salvando modelo em {output_dir}...")
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)
    print("   ✅ Modelo salvo")
    
    # Avaliar no conjunto de teste
    print(f"\n📊 Avaliando no conjunto de teste...")
    test_results = trainer.evaluate(test_dataset)
    
    print(f"\n🎯 Resultados no Teste:")
    print(f"   Accuracy:  {test_results['eval_accuracy']:.4f}")
    print(f"   F1 Score:  {test_results['eval_f1']:.4f}")
    print(f"   Precision: {test_results['eval_precision']:.4f}")
    print(f"   Recall:    {test_results['eval_recall']:.4f}")
    
    # Salvar resultados
    results = {
        "trained_at": datetime.utcnow().isoformat(),
        "model_name": model_name,
        "train_samples": len(train_dataset),
        "val_samples": len(val_dataset),
        "test_samples": len(test_dataset),
        "hyperparameters": {
            "max_length": max_length,
            "batch_size": batch_size,
            "num_epochs": num_epochs,
            "learning_rate": learning_rate
        },
        "train_results": {
            "loss": train_result.training_loss,
            "runtime": train_result.metrics["train_runtime"],
            "samples_per_second": train_result.metrics["train_samples_per_second"],
        },
        "test_results": test_results
    }
    
    results_path = os.path.join(output_dir, "training_results.json")
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Resultados salvos em: {results_path}")
    print(f"\n🎉 Modelo pronto em: {output_dir}")
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Treina classificador de currículos")
    parser.add_argument("--data-dir", default="data/training", help="Diretório com dados")
    parser.add_argument("--model", default="distilbert-base-uncased", help="Modelo HuggingFace")
    parser.add_argument("--output-dir", default="models/resume_classifier", help="Onde salvar modelo")
    parser.add_argument("--max-length", type=int, default=512, help="Max tokens")
    parser.add_argument("--batch-size", type=int, default=16, help="Batch size")
    parser.add_argument("--epochs", type=int, default=3, help="Número de épocas")
    parser.add_argument("--lr", type=float, default=2e-5, help="Learning rate")
    parser.add_argument("--no-gpu", action="store_true", help="Não usar GPU")
    
    args = parser.parse_args()
    
    train_resume_classifier(
        data_dir=args.data_dir,
        model_name=args.model,
        output_dir=args.output_dir,
        max_length=args.max_length,
        batch_size=args.batch_size,
        num_epochs=args.epochs,
        learning_rate=args.lr,
        use_gpu=not args.no_gpu
    )
