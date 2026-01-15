import { useState, useRef, useEffect } from 'react';
import { Upload, FileText, CheckCircle, XCircle, Loader, AlertCircle } from 'lucide-react';
import api from '../services/api';
import type { Municipality, Document as DocType } from '../types';

export default function UploadPage() {
  const [states, setStates] = useState<string[]>([]);
  const [selectedState, setSelectedState] = useState<string>('');
  const [municipalities, setMunicipalities] = useState<Municipality[]>([]);
  const [selectedMunicipality, setSelectedMunicipality] = useState<string>('');
  const [documentType, setDocumentType] = useState<'LOA' | 'LDO'>('LOA');
  const [year, setYear] = useState<number>(new Date().getFullYear());
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [documents, setDocuments] = useState<DocType[]>([]);
  const [dragActive, setDragActive] = useState(false);
  const [pollingActive, setPollingActive] = useState(false);
  const [processingDocId, setProcessingDocId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    loadStates();
    loadDocuments();
  }, []);

  // Polling automático para verificar status de documentos em processamento
  useEffect(() => {
    const hasProcessingDocs = documents.some(
      doc => doc.status === 'pending' || doc.status === 'processing'
    );

    if (hasProcessingDocs && !pollingActive) {
      console.log('[POLLING] 🔄 Starting automatic status polling...');
      setPollingActive(true);
      
      pollingIntervalRef.current = setInterval(() => {
        console.log('[POLLING] 📊 Checking document statuses...');
        loadDocuments();
      }, 5000); // Verifica a cada 5 segundos
    } else if (!hasProcessingDocs && pollingActive) {
      console.log('[POLLING] ✅ All documents processed, stopping polling');
      setPollingActive(false);
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    }
  }, [documents, pollingActive]);

  // Cleanup do polling quando componente desmonta
  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        console.log('[POLLING] 🛑 Component unmounting, clearing interval');
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (selectedState) {
      loadMunicipalities(selectedState);
    } else {
      setMunicipalities([]);
      setSelectedMunicipality('');
    }
  }, [selectedState]);

  const loadStates = async () => {
    try {
      const response = await api.get('/municipalities/states');
      setStates(response.data);
    } catch (error) {
      console.error('Erro ao carregar estados:', error);
    }
  };

  const loadMunicipalities = async (state: string) => {
    try {
      const response = await api.get('/municipalities', {
        params: { state }
      });
      setMunicipalities(response.data);
    } catch (error) {
      console.error('Erro ao carregar municípios:', error);
    }
  };

  const loadDocuments = async () => {
    try {
      console.log('[DOCUMENTS] 📥 Loading documents...');
      const response = await api.get('/documents');
      console.log('[DOCUMENTS] ✅ Loaded:', response.data.length, 'documents');
      
      // Para documentos em processamento, buscar progresso real do endpoint /progress
      const docsWithProgress = await Promise.all(
        response.data.map(async (doc: DocType) => {
          if (doc.status === 'processing') {
            try {
              console.log(`[PROGRESS] 📊 Fetching progress for ${doc.id}...`);
              const progressResponse = await api.get(`/documents/${doc.id}/progress`);
              console.log(`[PROGRESS] ✅ Progress: ${progressResponse.data.current_batch}/${progressResponse.data.total_batches}`);
              return {
                ...doc,
                processed_batches: progressResponse.data.current_batch,
                total_batches: progressResponse.data.total_batches
              };
            } catch (error) {
              console.warn(`[PROGRESS] ⚠️  Failed to get progress for ${doc.id}:`, error);
              return doc;
            }
          }
          return doc;
        })
      );
      
      // Detectar mudanças de status
      if (documents.length > 0) {
        docsWithProgress.forEach((newDoc: DocType) => {
          const oldDoc = documents.find(d => d.id === newDoc.id);
          if (oldDoc && oldDoc.status !== newDoc.status) {
            console.log(`[DOCUMENTS] 🔄 Status changed: ${oldDoc.type} ${oldDoc.status} → ${newDoc.status}`);
            if (newDoc.status === 'completed') {
              console.log('[DOCUMENTS] 🎉 Document processing completed!', newDoc.type);
            }
          }
        });
      }
      
      setDocuments(docsWithProgress);
    } catch (error) {
      console.error('[DOCUMENTS] ❌ Error loading documents:', error);
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleFileSelect = (selectedFile: File) => {
    if (selectedFile.type !== 'application/pdf') {
      setUploadError('Por favor, selecione apenas arquivos PDF');
      return;
    }

    if (selectedFile.size > 50 * 1024 * 1024) {
      setUploadError('O arquivo não pode ser maior que 50MB');
      return;
    }

    setFile(selectedFile);
    setUploadError(null);
    setUploadSuccess(false);
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelect(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!selectedMunicipality || !file) {
      setUploadError('Por favor, selecione um município e um arquivo');
      return;
    }

    console.log('[UPLOAD] 🚀 Starting upload...', {
      file: file.name,
      size: `${(file.size / 1024 / 1024).toFixed(2)}MB`,
      pages: 'estimating...',
      municipality: selectedMunicipality,
      type: documentType,
      year: year
    });

    setUploading(true);
    setUploadProgress(0);
    setUploadError(null);
    setUploadSuccess(false);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('municipality_id', selectedMunicipality);
    formData.append('doc_type', documentType);  // Backend espera 'doc_type', não 'document_type'
    formData.append('year', year.toString());

    const startTime = Date.now();

    try {
      const response = await api.post('/documents/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            console.log(`[UPLOAD] 📊 Progress: ${progress}%`);
            setUploadProgress(progress);
          }
        },
      });

      const uploadTime = ((Date.now() - startTime) / 1000).toFixed(2);
      console.log('[UPLOAD] ✅ Upload completed successfully!', {
        time: `${uploadTime}s`,
        document_id: response.data.document_id,
        status: response.data.status,
        estimated_processing: response.data.estimated_processing_time_minutes
          ? `${response.data.estimated_processing_time_minutes} minutos`
          : 'N/A'
      });

      setUploadSuccess(true);
      setFile(null);
      setUploadProgress(0);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      
      // Recarregar lista de documentos
      setTimeout(() => {
        console.log('[UPLOAD] 🔄 Reloading documents list...');
        loadDocuments();
      }, 1000);

    } catch (error: any) {
      console.error('[UPLOAD] ❌ Upload failed:', {
        message: error.message,
        status: error.response?.status,
        detail: error.response?.data?.detail
      });
      setUploadError(
        error.response?.data?.detail || 
        'Erro ao fazer upload do documento. Tente novamente.'
      );
    } finally {
      setUploading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-green-600';
      case 'processing':
        return 'text-blue-600';
      case 'pending':
        return 'text-yellow-600';
      case 'failed':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5" />;
      case 'processing':
        return <Loader className="w-5 h-5 animate-spin" />;
      case 'pending':
        return <Loader className="w-5 h-5" />;
      case 'failed':
        return <XCircle className="w-5 h-5" />;
      default:
        return <FileText className="w-5 h-5" />;
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'pending':
        return 'Pendente';
      case 'processing':
        return 'Processando';
      case 'completed':
        return 'Processado';
      case 'failed':
        return 'Falhou';
      default:
        return status;
    }
  };

  const handleProcessDocument = async (documentId: string) => {
    console.log('[PROCESS] 🚀 Starting document processing...', { documentId });
    setProcessingDocId(documentId);

    try {
      // Inicia o processamento com timeout curto (não esperamos a resposta completa)
      const response = await api.post(`/documents/${documentId}/process`, {}, {
        timeout: 10000, // 10 segundos apenas para iniciar
      });
      console.log('[PROCESS] ✅ Processing started successfully!', response.data);
      
      // Recarregar documentos para atualizar status
      setTimeout(() => {
        loadDocuments();
      }, 2000);
    } catch (error: any) {
      // Se deu timeout, mas foi timeout esperado (processamento continua)
      if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
        console.log('[PROCESS] ⏱️ Request timed out, but processing continues in background...');
        // Recarregar documentos para ver se status mudou
        setTimeout(() => {
          loadDocuments();
        }, 2000);
      } else {
        console.error('[PROCESS] ❌ Failed to start processing:', {
          message: error.message,
          status: error.response?.status,
          detail: error.response?.data?.detail
        });
        alert(`Erro ao processar documento: ${error.response?.data?.detail || error.message}`);
      }
    } finally {
      setProcessingDocId(null);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Upload de Documentos</h1>
        <p className="text-gray-600 mt-2">
          Faça upload dos documentos LOA e LDO em formato PDF.
        </p>
      </div>

      {/* Upload Card */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="space-y-6">
          {/* Estado */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Estado *
            </label>
            <select
              value={selectedState}
              onChange={(e) => setSelectedState(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={uploading}
            >
              <option value="">Selecione um estado</option>
              {states.map((state) => (
                <option key={state} value={state}>
                  {state}
                </option>
              ))}
            </select>
          </div>

          {/* Município */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Município *
            </label>
            <select
              value={selectedMunicipality}
              onChange={(e) => setSelectedMunicipality(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={uploading || !selectedState}
            >
              <option value="">
                {selectedState ? 'Selecione um município' : 'Selecione um estado primeiro'}
              </option>
              {municipalities.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name} ({m.year})
                </option>
              ))}
            </select>
            {selectedState && municipalities.length === 0 && (
              <p className="text-sm text-gray-500 mt-1">
                Nenhum município cadastrado para {selectedState}
              </p>
            )}
          </div>

          {/* Tipo e Ano */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Tipo de Documento *
              </label>
              <select
                value={documentType}
                onChange={(e) => setDocumentType(e.target.value as 'LOA' | 'LDO')}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                disabled={uploading}
              >
                <option value="LOA">LOA - Lei Orçamentária Anual</option>
                <option value="LDO">LDO - Lei de Diretrizes Orçamentárias</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Ano *
              </label>
              <input
                type="number"
                value={year}
                onChange={(e) => setYear(Number(e.target.value))}
                min={2000}
                max={2100}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                disabled={uploading}
              />
            </div>
          </div>

          {/* Drag & Drop Area */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Arquivo PDF *
            </label>
            <div
              className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                dragActive
                  ? 'border-blue-500 bg-blue-50'
                  : file
                  ? 'border-green-500 bg-green-50'
                  : 'border-gray-300 hover:border-gray-400'
              }`}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf"
                onChange={handleFileInputChange}
                className="hidden"
                disabled={uploading}
              />

              {file ? (
                <div className="space-y-2">
                  <FileText className="w-12 h-12 text-green-600 mx-auto" />
                  <p className="text-sm font-medium text-gray-900">{file.name}</p>
                  <p className="text-xs text-gray-500">
                    {(file.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                  <button
                    onClick={() => {
                      setFile(null);
                      if (fileInputRef.current) {
                        fileInputRef.current.value = '';
                      }
                    }}
                    className="text-sm text-blue-600 hover:text-blue-700"
                    disabled={uploading}
                  >
                    Escolher outro arquivo
                  </button>
                </div>
              ) : (
                <div className="space-y-2">
                  <Upload className="w-12 h-12 text-gray-400 mx-auto" />
                  <p className="text-sm text-gray-600">
                    Arraste e solte o arquivo PDF aqui
                  </p>
                  <p className="text-xs text-gray-500">ou</p>
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="text-sm text-blue-600 hover:text-blue-700 font-medium"
                    disabled={uploading}
                  >
                    Clique para selecionar
                  </button>
                  <p className="text-xs text-gray-500 mt-2">
                    Tamanho máximo: 50MB
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Progress Bar */}
          {uploading && (
            <div className="space-y-2">
              <div className="flex justify-between text-sm text-gray-600">
                <span>Fazendo upload...</span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}

          {/* Success Message */}
          {uploadSuccess && (
            <div className="flex items-center gap-2 p-4 bg-green-50 border border-green-200 rounded-lg">
              <CheckCircle className="w-5 h-5 text-green-600" />
              <p className="text-sm text-green-800">
                Documento enviado com sucesso! O processamento começará em breve.
              </p>
            </div>
          )}

          {/* Error Message */}
          {uploadError && (
            <div className="flex items-center gap-2 p-4 bg-red-50 border border-red-200 rounded-lg">
              <AlertCircle className="w-5 h-5 text-red-600" />
              <p className="text-sm text-red-800">{uploadError}</p>
            </div>
          )}

          {/* Upload Button */}
          <button
            onClick={handleUpload}
            disabled={!selectedMunicipality || !file || uploading}
            className="w-full py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
          >
            {uploading ? 'Enviando...' : 'Fazer Upload'}
          </button>
        </div>
      </div>

      {/* Documents List */}
      {documents.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-gray-900">
              Documentos Enviados
            </h2>
            {pollingActive && (
              <div className="flex items-center gap-2 text-sm text-blue-600">
                <Loader className="w-4 h-4 animate-spin" />
                <span>Verificando status...</span>
              </div>
            )}
          </div>
          <div className="space-y-3">
            {documents.map((doc) => (
              <div
                key={doc.id}
                className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className={getStatusColor(doc.status)}>
                    {getStatusIcon(doc.status)}
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">
                      {doc.type}
                    </p>
                    <p className="text-sm text-gray-600">{doc.filename}</p>
                    {doc.status === 'processing' && (
                      <div className="mt-2 space-y-2">
                        {doc.total_batches > 0 && doc.processed_batches > 0 ? (
                          <>
                            <div className="flex justify-between text-xs text-gray-600">
                              <span>Processando embeddings...</span>
                              <span className="font-medium text-blue-600">
                                {doc.processed_batches}/{doc.total_batches} batches ({Math.round((doc.processed_batches / doc.total_batches) * 100)}%)
                              </span>
                            </div>
                            <div className="w-full bg-gray-200 rounded-full h-2">
                              <div
                                className="bg-blue-600 h-2 rounded-full transition-all duration-500"
                                style={{ width: `${(doc.processed_batches / doc.total_batches) * 100}%` }}
                              />
                            </div>
                            <p className="text-xs text-gray-500">
                              Tempo estimado restante: ~{Math.ceil((doc.total_batches - doc.processed_batches) * 5 / 60)} minutos
                            </p>
                          </>
                        ) : (
                          <div className="flex items-center gap-2">
                            <div className="flex space-x-1">
                              <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{animationDelay: '0ms'}}></div>
                              <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{animationDelay: '150ms'}}></div>
                              <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{animationDelay: '300ms'}}></div>
                            </div>
                            <p className="text-xs text-blue-600">
                              Iniciando processamento...
                            </p>
                          </div>
                        )}
                      </div>
                    )}
                    {doc.status === 'pending' && (
                      <p className="text-xs text-gray-600 mt-1">
                        Aguardando processamento...
                      </p>
                    )}
                  </div>
                </div>
                <div className="text-right flex flex-col items-end gap-2">
                  <span
                    className={`text-sm font-medium ${getStatusColor(doc.status)}`}
                  >
                    {getStatusLabel(doc.status)}
                  </span>
                  <p className="text-xs text-gray-500">
                    {new Date(doc.upload_date).toLocaleDateString('pt-BR', {
                      day: '2-digit',
                      month: '2-digit',
                      year: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </p>
                  {doc.status === 'pending' && (
                    <button
                      onClick={() => handleProcessDocument(doc.id)}
                      disabled={processingDocId === doc.id}
                      className="flex items-center gap-1 px-3 py-1 text-sm font-medium text-white bg-green-600 rounded hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
                    >
                      {processingDocId === doc.id ? (
                        <>
                          <Loader className="w-4 h-4 animate-spin" />
                          Iniciando...
                        </>
                      ) : (
                        <>
                          ▶️ Processar
                        </>
                      )}
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

