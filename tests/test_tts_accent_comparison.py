#!/usr/bin/env python3
"""
TTS Accent Comparison Script
=============================

Genera muestras de audio usando diferentes modelos y configuraciones TTS
para comparar calidad de acento italiano.

Modelos probados:
1. OpenAI tts-1 (standard quality, cheaper)
2. OpenAI tts-1-hd (high definition, 2x price)
3. OpenAI gpt-4o-audio-preview (accent-steered, 4x price)

Voces probadas para cada modelo:
- alloy (neutral, recommended)
- nova (feminine)
- echo (masculine)
- fable (masculine, British accent)

Output: test_audio_samples/ directory with organized samples
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import base64
from typing import Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# This file is a manual comparison script (generates audio samples). It is not an
# automated pytest test, but it lives under tests/ for convenience.
if __name__ != "__main__":
    import pytest

    pytest.skip(
        "Manual script (not an automated test). Run: python tests/test_tts_accent_comparison.py",
        allow_module_level=True,
    )

try:
    from openai import OpenAI
    import config
    from loguru import logger
except ImportError as e:
    print(f"ERROR: Missing dependencies. Run: pip install openai loguru")
    print(f"Details: {e}")
    sys.exit(1)


# ============================================================================
# TEST TEXTS - Variedad de contenido italiano
# ============================================================================

TEST_TEXTS = {
    "greeting": {
        "label": "1. Saludo profesional",
        "text": "Buongiorno, sono il suo commercialista di fiducia. Come posso aiutarla oggi?"
    },
    "technical": {
        "label": "2. Términos técnicos fiscales",
        "text": "La dichiarazione IVA trimestrale deve essere presentata entro il giorno quindici del mese successivo al trimestre di riferimento."
    },
    "numbers": {
        "label": "3. Números y porcentajes",
        "text": "L'aliquota IRES ordinaria è del ventiquattro per cento, mentre per le società di capitali l'IVA può variare dal quattro al ventidue per cento."
    },
    "complex": {
        "label": "4. Respuesta compleja (real)",
        "text": "Dunque, per quanto riguarda la sua domanda sulle deduzioni fiscali, le spiego meglio. Secondo la normativa vigente, le spese di carburante sono deducibili al venti per cento per i veicoli aziendali. Tuttavia, se il veicolo è utilizzato esclusivamente per l'attività professionale, la percentuale di deduzione può aumentare fino all'ottanta per cento. Le consiglio di conservare tutti i documenti giustificativi."
    },
    "difficult_words": {
        "label": "5. Palabras difíciles de pronunciar",
        "text": "Gli adempimenti fiscali richiedono particolare attenzione: dichiarazione, registrazione, liquidazione, ritenuta d'acconto, contribuzione previdenziale."
    }
}


# ============================================================================
# TTS MODEL CONFIGURATIONS
# ============================================================================

TTS_CONFIGS = {
    # Standard TTS models
    "tts1_alloy": {
        "label": "OpenAI tts-1 (standard) - Voice: alloy",
        "model": "tts-1",
        "voice": "alloy",
        "method": "standard",
        "cost_per_1k_chars": 0.015,
        "description": "Modelo estándar, calidad básica, acento neutral/anglófono"
    },
    "tts1_nova": {
        "label": "OpenAI tts-1 (standard) - Voice: nova",
        "model": "tts-1",
        "voice": "nova",
        "method": "standard",
        "cost_per_1k_chars": 0.015,
        "description": "Modelo estándar, voz femenina, acento neutral"
    },
    "tts1_echo": {
        "label": "OpenAI tts-1 (standard) - Voice: echo",
        "model": "tts-1",
        "voice": "echo",
        "method": "standard",
        "cost_per_1k_chars": 0.015,
        "description": "Modelo estándar, voz masculina, acento neutral"
    },
    
    # HD TTS models
    "tts1hd_alloy": {
        "label": "OpenAI tts-1-hd (high def) - Voice: alloy",
        "model": "tts-1-hd",
        "voice": "alloy",
        "method": "standard",
        "cost_per_1k_chars": 0.030,
        "description": "Modelo HD, mejor calidad audio, PERO sigue con acento anglófono"
    },
    "tts1hd_nova": {
        "label": "OpenAI tts-1-hd (high def) - Voice: nova",
        "model": "tts-1-hd",
        "voice": "nova",
        "method": "standard",
        "cost_per_1k_chars": 0.030,
        "description": "Modelo HD, voz femenina, acento neutral"
    },
    
    # Accent-steered models (gpt-4o-audio-preview)
    "gpt4o_audio_alloy_light": {
        "label": "GPT-4o Audio Preview - Accent: Italian (light instructions)",
        "model": "gpt-4o-audio-preview",
        "voice": "alloy",
        "method": "accent_steered_light",
        "cost_per_1k_chars": 0.060,
        "description": "Modelo avanzado con instrucciones LIGERAS de acento italiano"
    },
    "gpt4o_audio_alloy_strong": {
        "label": "GPT-4o Audio Preview - Accent: Italian (strong instructions)",
        "model": "gpt-4o-audio-preview",
        "voice": "alloy",
        "method": "accent_steered_strong",
        "cost_per_1k_chars": 0.060,
        "description": "Modelo avanzado con instrucciones FUERTES de acento milanés"
    },
    "gpt4o_audio_nova": {
        "label": "GPT-4o Audio Preview - Voice: nova + Italian accent",
        "model": "gpt-4o-audio-preview",
        "voice": "nova",
        "method": "accent_steered_strong",
        "cost_per_1k_chars": 0.060,
        "description": "Modelo avanzado, voz femenina, acento italiano fuerte"
    }
}


# ============================================================================
# ACCENT INSTRUCTION PROMPTS
# ============================================================================

ACCENT_PROMPTS = {
    "accent_steered_light": """Parla come un madrelingua italiano.
Usa intonazione naturale italiana, non neutra o anglosassone.
Pronuncia con accento italiano autentico.""",
    
    "accent_steered_strong": """Parla ESATTAMENTE come un commercialista MILANESE di 45-50 anni.

ACCENTO SPECIFICO RICHIESTO:
- Accento lombardo leggero (Milano/Monza)
- Vocali "o" e "e" tipiche del nord Italia
- Consonanti doppie ben marcate
- Ritmo moderato, professionale

PRONUNCIA CRITICA:
- "dichiarazione" → consonanti dure, vocali aperte
- "IVA" → pronuncia I-VA (italiana), non "aiva" (anglofona)
- "IRES" → I-RES con R italiana rolling
- Numeri in italiano: "quindici", "ventiquattro" con cadenza naturale

STILE VOCALE:
- Tono professionale ma cordiale
- Come un commercialista milanese che parla con un cliente
- Sicuro e competente, non robotico

FONDAMENTALE:
Zero tracce di pronuncia straniera. Parli italiano dalla nascita."""
}


# ============================================================================
# TTS GENERATOR CLASS
# ============================================================================

class TTSComparator:
    """Compara diferentes modelos y configuraciones TTS"""
    
    def __init__(self, output_dir: str = "test_audio_samples"):
        """Initialize TTS comparator"""
        
        # Check API key
        if not config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not found in config/environment")
        
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Create timestamp for this test run
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_dir = self.output_dir / f"run_{self.timestamp}"
        self.run_dir.mkdir(exist_ok=True)
        
        logger.info(f"Output directory: {self.run_dir}")
        
        # Track costs
        self.total_chars = 0
        self.total_cost = 0.0
        self.results = []
    
    def generate_standard_tts(
        self,
        text: str,
        model: str,
        voice: str
    ) -> bytes:
        """Generate audio using standard TTS API"""
        
        response = self.client.audio.speech.create(
            model=model,
            voice=voice,
            input=text,
            response_format="mp3"
        )
        
        return response.content
    
    def generate_accent_steered_tts(
        self,
        text: str,
        voice: str,
        accent_method: str
    ) -> bytes:
        """Generate audio using gpt-4o-audio-preview with accent steering"""
        
        system_prompt = ACCENT_PROMPTS.get(
            accent_method,
            ACCENT_PROMPTS["accent_steered_light"]
        )
        
        completion = self.client.chat.completions.create(
            model="gpt-4o-audio-preview",
            modalities=["text", "audio"],
            audio={
                "voice": voice,
                "format": "mp3"
            },
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": text
                }
            ],
        )
        
        # Decode base64 audio
        audio_data = completion.choices[0].message.audio.data
        mp3_bytes = base64.b64decode(audio_data)
        
        return mp3_bytes
    
    def generate_sample(
        self,
        text_key: str,
        text_content: str,
        config_key: str,
        config: Dict
    ) -> Dict:
        """Generate a single audio sample"""
        
        logger.info(f"Generating: {config_key} for text: {text_key}")
        
        try:
            # Generate audio based on method
            if config["method"] == "standard":
                audio_bytes = self.generate_standard_tts(
                    text_content,
                    config["model"],
                    config["voice"]
                )
            else:
                # Accent-steered method
                audio_bytes = self.generate_accent_steered_tts(
                    text_content,
                    config["voice"],
                    config["method"]
                )
            
            # Save audio file
            filename = f"{text_key}_{config_key}.mp3"
            filepath = self.run_dir / filename
            
            with open(filepath, "wb") as f:
                f.write(audio_bytes)
            
            # Calculate cost
            char_count = len(text_content)
            cost = (char_count / 1000) * config["cost_per_1k_chars"]
            
            self.total_chars += char_count
            self.total_cost += cost
            
            result = {
                "text_key": text_key,
                "config_key": config_key,
                "filepath": str(filepath),
                "filename": filename,
                "model": config["model"],
                "voice": config["voice"],
                "method": config["method"],
                "chars": char_count,
                "cost_usd": cost,
                "description": config["description"],
                "status": "SUCCESS"
            }
            
            logger.success(f"✓ Generated: {filename} (${cost:.4f})")
            return result
            
        except Exception as e:
            logger.error(f"✗ Failed: {config_key} - {str(e)}")
            return {
                "text_key": text_key,
                "config_key": config_key,
                "status": "FAILED",
                "error": str(e)
            }
    
    def generate_all_samples(
        self,
        text_keys: List[str] = None,
        config_keys: List[str] = None
    ):
        """Generate all combinations of texts and configs"""
        
        # Default to all texts and configs
        if text_keys is None:
            text_keys = list(TEST_TEXTS.keys())
        if config_keys is None:
            config_keys = list(TTS_CONFIGS.keys())
        
        logger.info(f"Generating {len(text_keys)} texts × {len(config_keys)} configs = {len(text_keys) * len(config_keys)} samples")
        
        for text_key in text_keys:
            text_data = TEST_TEXTS[text_key]
            logger.info(f"\n{'='*60}")
            logger.info(f"{text_data['label']}")
            logger.info(f"{'='*60}")
            
            for config_key in config_keys:
                config = TTS_CONFIGS[config_key]
                
                result = self.generate_sample(
                    text_key,
                    text_data["text"],
                    config_key,
                    config
                )
                
                self.results.append(result)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"GENERATION COMPLETE")
        logger.info(f"{'='*60}")
        logger.info(f"Total samples: {len(self.results)}")
        logger.info(f"Total characters: {self.total_chars:,}")
        logger.info(f"Total cost: ${self.total_cost:.2f}")
    
    def generate_report(self):
        """Generate comparison report"""
        
        report_path = self.run_dir / "COMPARISON_REPORT.md"
        
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# TTS ACCENT COMPARISON REPORT\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Total Samples:** {len(self.results)}\n")
            f.write(f"**Total Cost:** ${self.total_cost:.2f} USD\n\n")
            
            f.write("---\n\n")
            f.write("## 📊 RESULTS BY TEXT TYPE\n\n")
            
            # Group by text type
            for text_key, text_data in TEST_TEXTS.items():
                f.write(f"### {text_data['label']}\n\n")
                f.write(f"**Text:** _{text_data['text']}_\n\n")
                
                # List all samples for this text
                text_results = [r for r in self.results if r["text_key"] == text_key and r["status"] == "SUCCESS"]
                
                if text_results:
                    f.write("| Model | Voice | Method | Cost | File |\n")
                    f.write("|-------|-------|--------|------|------|\n")
                    
                    for result in text_results:
                        f.write(f"| {result['model']} | {result['voice']} | {result['method']} | ${result['cost_usd']:.4f} | `{result['filename']}` |\n")
                
                f.write("\n")
            
            f.write("---\n\n")
            f.write("## 🎯 CONFIGURATIONS TESTED\n\n")
            
            for config_key, config in TTS_CONFIGS.items():
                f.write(f"### {config['label']}\n\n")
                f.write(f"- **Model:** {config['model']}\n")
                f.write(f"- **Voice:** {config['voice']}\n")
                f.write(f"- **Method:** {config['method']}\n")
                f.write(f"- **Cost:** ${config['cost_per_1k_chars']:.3f} per 1K chars\n")
                f.write(f"- **Description:** {config['description']}\n\n")
            
            f.write("---\n\n")
            f.write("## 🎧 HOW TO COMPARE\n\n")
            f.write("1. **Busca el mismo texto** en diferentes archivos (ej: `greeting_*.mp3`)\n")
            f.write("2. **Escucha las versiones** una tras otra\n")
            f.write("3. **Evalúa:**\n")
            f.write("   - ¿Suena italiano nativo o extranjero?\n")
            f.write("   - ¿Las vocales son italianas o anglófonas?\n")
            f.write("   - ¿La entonación es natural?\n")
            f.write("   - ¿La pronunciación de términos técnicos es correcta?\n\n")
            
            f.write("## 💡 RECOMMENDATIONS\n\n")
            f.write("**Para DEMO rápido (precio bajo):**\n")
            f.write("- `tts1hd_alloy` o `tts1hd_nova` (mejor calidad que tts-1)\n")
            f.write("- Costo: ~$0.03/1K chars\n")
            f.write("- Limitación: Acento anglófono persiste\n\n")
            
            f.write("**Para PRODUCCIÓN (calidad profesional):**\n")
            f.write("- `gpt4o_audio_alloy_strong` (acento italiano fuerte)\n")
            f.write("- Costo: ~$0.06/1K chars (2x más caro que HD)\n")
            f.write("- Ventaja: Acento italiano nativo\n\n")
            
            f.write("**Si NINGUNO convence:**\n")
            f.write("- Migrar a ElevenLabs (voces nativas italianas reales)\n")
            f.write("- Costo: ~$0.30/1K chars (5x más caro)\n")
            f.write("- Garantía: Calidad profesional broadcasting\n\n")
        
        logger.success(f"Report generated: {report_path}")
        return report_path
    
    def generate_html_player(self):
        """Generate HTML player for easy comparison"""
        
        html_path = self.run_dir / "player.html"
        
        with open(html_path, "w", encoding="utf-8") as f:
            f.write("""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TTS Accent Comparison Player</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        h1 {
            color: #2c3e50;
            text-align: center;
        }
        .text-section {
            background: white;
            padding: 20px;
            margin: 20px 0;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .text-content {
            background: #f8f9fa;
            padding: 15px;
            border-left: 4px solid #3498db;
            margin: 10px 0;
            font-style: italic;
        }
        .audio-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        .audio-item {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 4px;
            border: 1px solid #dee2e6;
        }
        .audio-label {
            font-weight: bold;
            color: #495057;
            margin-bottom: 8px;
            font-size: 14px;
        }
        .audio-description {
            font-size: 12px;
            color: #6c757d;
            margin-bottom: 10px;
        }
        .cost-badge {
            display: inline-block;
            background: #28a745;
            color: white;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 11px;
            margin-left: 5px;
        }
        .cost-badge.expensive {
            background: #ffc107;
            color: #000;
        }
        audio {
            width: 100%;
            margin-top: 5px;
        }
        .legend {
            background: #fff;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .legend-item {
            display: inline-block;
            margin-right: 20px;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <h1>🎧 TTS Accent Comparison Player</h1>
    
    <div class="legend">
        <strong>Leyenda de costos:</strong>
        <span class="legend-item"><span class="cost-badge">$</span> Standard ($0.015-0.03/1K)</span>
        <span class="legend-item"><span class="cost-badge expensive">$$</span> Premium ($0.06/1K)</span>
    </div>
    
""")
            
            # Group results by text type
            for text_key, text_data in TEST_TEXTS.items():
                text_results = [r for r in self.results if r["text_key"] == text_key and r["status"] == "SUCCESS"]
                
                if not text_results:
                    continue
                
                f.write(f'    <div class="text-section">\n')
                f.write(f'        <h2>{text_data["label"]}</h2>\n')
                f.write(f'        <div class="text-content">{text_data["text"]}</div>\n')
                f.write(f'        <div class="audio-grid">\n')
                
                for result in text_results:
                    config = TTS_CONFIGS[result["config_key"]]
                    cost_class = "expensive" if result["cost_usd"] > 0.04 else ""
                    
                    f.write(f'            <div class="audio-item">\n')
                    f.write(f'                <div class="audio-label">\n')
                    f.write(f'                    {config["model"]} - {config["voice"]}\n')
                    f.write(f'                    <span class="cost-badge {cost_class}">${result["cost_usd"]:.4f}</span>\n')
                    f.write(f'                </div>\n')
                    f.write(f'                <div class="audio-description">{config["description"]}</div>\n')
                    f.write(f'                <audio controls preload="none">\n')
                    f.write(f'                    <source src="{result["filename"]}" type="audio/mpeg">\n')
                    f.write(f'                </audio>\n')
                    f.write(f'            </div>\n')
                
                f.write(f'        </div>\n')
                f.write(f'    </div>\n\n')
            
            f.write("""
</body>
</html>
""")
        
        logger.success(f"HTML player generated: {html_path}")
        logger.info(f"Open in browser: file://{html_path.absolute()}")
        return html_path


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main execution"""
    
    print("\n" + "="*70)
    print("  TTS ACCENT COMPARISON TOOL")
    print("  Genera muestras de audio para comparar acentos")
    print("="*70 + "\n")
    
    # Ask user which configs to test
    print("¿Qué configuraciones quieres probar?\n")
    print("1. TODAS (recomendado) - ~7 configs × 5 textos = 35 samples (~$0.50)")
    print("2. SOLO COMPARACIÓN RÁPIDA - 3 mejores opciones × 2 textos = 6 samples (~$0.10)")
    print("3. PERSONALIZADO - selecciona configs manualmente\n")
    
    choice = input("Selección (1/2/3) [default: 2]: ").strip() or "2"
    
    if choice == "1":
        # All configs
        config_keys = list(TTS_CONFIGS.keys())
        text_keys = list(TEST_TEXTS.keys())
    elif choice == "2":
        # Quick comparison - best options only
        config_keys = [
            "tts1hd_alloy",  # Standard HD baseline
            "gpt4o_audio_alloy_strong",  # Accent steered (recommended)
            "gpt4o_audio_nova"  # Alternative voice
        ]
        text_keys = ["greeting", "technical"]  # Just 2 representative texts
    else:
        # Custom selection
        print("\nConfigs disponibles:")
        for i, (key, cfg) in enumerate(TTS_CONFIGS.items(), 1):
            print(f"{i}. {cfg['label']}")
        
        selected = input("\nNúmeros separados por coma (ej: 1,3,5): ").strip()
        indices = [int(x.strip())-1 for x in selected.split(",")]
        config_keys = [list(TTS_CONFIGS.keys())[i] for i in indices]
        
        text_keys = list(TEST_TEXTS.keys())
    
    print(f"\n✓ Generando {len(config_keys)} configs × {len(text_keys)} textos = {len(config_keys) * len(text_keys)} samples\n")
    
    # Create comparator and generate
    comparator = TTSComparator()
    
    try:
        comparator.generate_all_samples(text_keys, config_keys)
        
        # Generate reports
        report_path = comparator.generate_report()
        html_path = comparator.generate_html_player()
        
        print("\n" + "="*70)
        print("  ✅ GENERATION COMPLETE!")
        print("="*70)
        print(f"\nTotal samples: {len(comparator.results)}")
        print(f"Total cost: ${comparator.total_cost:.2f} USD")
        print(f"\nOutput directory: {comparator.run_dir}")
        print(f"\n📄 Report: {report_path}")
        print(f"🎧 Player: {html_path}")
        print(f"\n💡 Abre player.html en tu navegador para comparar fácilmente")
        
    except Exception as e:
        logger.error(f"Error during generation: {e}")
        logger.exception("Full traceback:")
        sys.exit(1)


if __name__ == "__main__":
    main()