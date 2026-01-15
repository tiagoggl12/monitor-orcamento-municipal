"""
Wrapper para Google Gemini com configuração de timeout personalizada usando API REST.
"""

import requests
import json
from typing import Any, Dict, Optional


class GeminiResponse:
    """Objeto de resposta compatível com o SDK do Gemini."""
    
    def __init__(self, text: str):
        self.text = text


class GeminiWithTimeout:
    """Cliente Gemini usando API REST com timeout configurável."""
    
    def __init__(self, api_key: str, model_name: str = "gemini-2.5-pro", timeout: int = 600):
        """
        Inicializa o cliente com timeout configurado.
        
        Args:
            api_key: Chave da API do Gemini
            model_name: Nome do modelo (padrão: gemini-2.5-pro)
            timeout: Timeout em segundos (padrão: 600 = 10 minutos)
        """
        self.api_key = api_key
        self.model_name = model_name
        self.timeout = timeout
        self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
    
    def generate_content(
        self,
        prompt: str,
        generation_config: Optional[Any] = None,
        **kwargs
    ) -> GeminiResponse:
        """
        Gera conteúdo com timeout configurado usando API REST.
        
        Args:
            prompt: Prompt para o modelo
            generation_config: Configurações de geração
            **kwargs: Argumentos adicionais
            
        Returns:
            Resposta do modelo (objeto compatível)
        """
        # Construir payload
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }
        
        # Adicionar configurações de geração
        if generation_config:
            config_dict = {}
            if hasattr(generation_config, 'temperature'):
                config_dict['temperature'] = generation_config.temperature
            if hasattr(generation_config, 'max_output_tokens'):
                config_dict['maxOutputTokens'] = generation_config.max_output_tokens
            if hasattr(generation_config, 'top_p'):
                config_dict['topP'] = generation_config.top_p
            if hasattr(generation_config, 'top_k'):
                config_dict['topK'] = generation_config.top_k
            
            if config_dict:
                payload['generationConfig'] = config_dict
        
        # Fazer requisição com timeout personalizado
        response = requests.post(
            f"{self.base_url}?key={self.api_key}",
            json=payload,
            timeout=self.timeout,
            headers={"Content-Type": "application/json"}
        )
        
        # Verificar erros
        response.raise_for_status()
        
        # Extrair texto da resposta
        result = response.json()
        text = result['candidates'][0]['content']['parts'][0]['text']
        
        return GeminiResponse(text)


def create_gemini_client(api_key: str, timeout: int = 600) -> GeminiWithTimeout:
    """
    Cria um cliente Gemini com timeout configurado.
    
    Args:
        api_key: Chave da API do Gemini
        timeout: Timeout em segundos
        
    Returns:
        Cliente Gemini configurado
    """
    return GeminiWithTimeout(api_key, timeout=timeout)
