import { useState, useEffect, useCallback, useRef } from 'react';
import { Search, RefreshCw, Trash2, CheckSquare, Square, Play, AlertCircle, CheckCircle, XCircle } from 'lucide-react';
import axios from 'axios';

interface Package {
  name: string;
  selected: boolean;
  processed?: boolean;
  last_processed?: string;
  total_documents?: number;
}

interface Job {
  job_id: string;
  status: string;
  total_packages: number;
  processed_packages: number;
  failed_packages: number;
  total_documents: number;
  current_package?: string;
}

interface Progress {
  current_package_index?: number;
  total_packages?: number;
  current_batch?: number;
  total_batches?: number;
  message: string;
  percentage: number;
  documents_inserted: number;
}

const api = axios.create({
  baseURL: 'http://localhost:4001/api'
});

export default function PortalIngestPage() {
  const [packages, setPackages] = useState<Package[]>([]);
  const [collections, setCollections] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [currentJob, setCurrentJob] = useState<Job | null>(null);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [error, setError] = useState<string>('');
  const pollingIntervalRef = useRef<number | null>(null);
  const activeJobIdRef = useRef<string | null>(null);
  
  // Funções de check com useCallback para evitar recriação
  const checkJobStatus = useCallback(async (jobId: string) => {
    try {
      const response = await api.get(`/portal/ingest/status/${jobId}`);
      
      // Só atualizar se houver mudanças significativas
      setCurrentJob(prevJob => {
        const apiJob = response.data;
        // Mapear campo "id" para "job_id" (API usa "id", frontend usa "job_id")
        const newJob = {
          job_id: apiJob.id,
          status: apiJob.status,
          total_packages: apiJob.total_packages,
          processed_packages: apiJob.processed_packages,
          failed_packages: apiJob.failed_packages,
          total_documents: apiJob.total_documents,
          current_package: apiJob.current_package
        };
        
        // Se não há job anterior, sempre atualizar
        if (!prevJob) return newJob;
        
        // Comparar campos importantes
        const hasChanged = 
          prevJob.processed_packages !== newJob.processed_packages ||
          prevJob.failed_packages !== newJob.failed_packages ||
          prevJob.total_documents !== newJob.total_documents ||
          prevJob.status !== newJob.status ||
          prevJob.current_package !== newJob.current_package;
        
        return hasChanged ? newJob : prevJob;
      });
      
      if (response.data.status === 'completed' || response.data.status === 'failed') {
        setProcessing(false);
        setProgress(null);
        loadCollections();
        loadProcessedPackages();
        setPackages(prevPackages => prevPackages.map(pkg => ({ ...pkg, selected: false })));
      }
    } catch (err) {
      console.error('Erro ao verificar status do job:', err);
    }
  }, []);
  
  const checkJobProgress = useCallback(async (jobId: string) => {
    try {
      const response = await api.get(`/portal/ingest/progress/${jobId}`);
      setProgress(response.data);
      console.log('[PROGRESS]', response.data);
    } catch (err) {
      console.error('Erro ao verificar progresso do job:', err);
    }
  }, []);
  
  useEffect(() => {
    loadPackages();
    loadCollections();
    loadProcessedPackages();
    checkForActiveJob();
  }, []);
  
  // Effect para gerenciar o polling
  useEffect(() => {
    const jobId = currentJob?.job_id;
    const jobStatus = currentJob?.status;
    const isActive = jobStatus === 'processing' || jobStatus === 'pending';
    
    // Se o job mudou ou não está mais ativo, limpar polling
    if (activeJobIdRef.current !== jobId) {
      console.log('[POLLING] Job mudou de', activeJobIdRef.current, 'para', jobId);
      if (pollingIntervalRef.current) {
        console.log('[POLLING] Parando polling anterior');
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
      activeJobIdRef.current = jobId || null;
    }
    
    // Iniciar polling se há um job ativo e ainda não está fazendo polling
    if (jobId && isActive && !pollingIntervalRef.current) {
      console.log('[POLLING] Iniciando polling para job:', jobId);
      
      // Fazer a primeira chamada imediatamente
      checkJobStatus(jobId);
      checkJobProgress(jobId);
      
      // Criar novo intervalo
      pollingIntervalRef.current = setInterval(() => {
        console.log('[POLLING] Tick - verificando status...');
        if (activeJobIdRef.current) {
          checkJobStatus(activeJobIdRef.current);
          checkJobProgress(activeJobIdRef.current);
        }
      }, 5000) as unknown as number;
      
      console.log('[POLLING] Intervalo criado:', pollingIntervalRef.current);
    }
    
    // Parar polling se o job não está mais ativo
    if (!isActive && pollingIntervalRef.current) {
      console.log('[POLLING] Job não está mais ativo, parando polling');
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
      activeJobIdRef.current = null;
    }
    
    // Cleanup apenas quando desmonta o componente
    return () => {
      if (pollingIntervalRef.current) {
        console.log('[POLLING] Componente desmontando - parando polling');
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentJob?.job_id, currentJob?.status]);
  
  const loadPackages = async () => {
    setLoading(true);
    try {
      const response = await api.get('/portal/packages');
      const packageList = response.data.packages.map((name: string) => ({
        name,
        selected: false,
        processed: false
      }));
      setPackages(packageList);
      
      // Após carregar packages, buscar quais foram processados
      await loadProcessedPackages();
    } catch (err) {
      console.error('Erro ao carregar packages:', err);
      setError('Erro ao carregar packages do Portal');
    } finally {
      setLoading(false);
    }
  };
  
  const loadProcessedPackages = async () => {
    try {
      const municResponse = await api.get('/municipalities/?state=CE');
      const fortaleza = municResponse.data.find((m: any) => m.name === 'Fortaleza');
      
      if (!fortaleza) {
        return;
      }
      
      const response = await api.get(`/portal/ingest/processed-packages?municipality_id=${fortaleza.id}`);
      const processedMap = response.data.processed_packages;
      
      // Atualizar packages com informações de processamento
      setPackages(prevPackages => 
        prevPackages.map(pkg => {
          const processedInfo = processedMap[pkg.name];
          if (processedInfo) {
            return {
              ...pkg,
              processed: true,
              last_processed: processedInfo.last_processed,
              total_documents: processedInfo.total_documents
            };
          }
          return pkg;
        })
      );
      
      console.log('[PROCESSED] Packages processados:', Object.keys(processedMap).length);
    } catch (err) {
      console.error('Erro ao carregar packages processados:', err);
    }
  };
  
  const checkForActiveJob = async () => {
    try {
      const municResponse = await api.get('/municipalities/?state=CE');
      const fortaleza = municResponse.data.find((m: any) => m.name === 'Fortaleza');
      
      if (!fortaleza) {
        return;
      }
      
      const response = await api.get(`/portal/ingest/active-job?municipality_id=${fortaleza.id}`);
      
      if (response.data.active_job) {
        const activeJob = response.data.active_job;
        console.log('[ACTIVE JOB] Job ativo encontrado:', activeJob.id);
        
        setCurrentJob({
          job_id: activeJob.id,
          status: activeJob.status,
          total_packages: activeJob.total_packages,
          processed_packages: activeJob.processed_packages,
          failed_packages: activeJob.failed_packages,
          total_documents: activeJob.total_documents,
          current_package: activeJob.current_package
        });
        
        setProcessing(true);
      } else {
        console.log('[ACTIVE JOB] Nenhum job ativo encontrado');
      }
    } catch (err) {
      console.error('Erro ao verificar job ativo:', err);
    }
  };
  
  const loadCollections = async () => {
    try {
      const response = await api.get('/portal/ingest/collections');
      setCollections(response.data.collections);
    } catch (err) {
      console.error('Erro ao carregar collections:', err);
    }
  };
  
  const togglePackage = (packageName: string) => {
    setPackages(packages.map(pkg =>
      pkg.name === packageName ? { ...pkg, selected: !pkg.selected } : pkg
    ));
  };
  
  const selectAll = () => {
    const filtered = getFilteredPackages();
    const allSelected = filtered.every(pkg => pkg.selected);
    
    setPackages(packages.map(pkg => {
      const isInFiltered = filtered.some(f => f.name === pkg.name);
      return isInFiltered ? { ...pkg, selected: !allSelected } : pkg;
    }));
  };
  
  const getFilteredPackages = () => {
    return packages.filter(pkg =>
      pkg.name.toLowerCase().includes(searchTerm.toLowerCase())
    );
  };
  
  const startProcessing = async () => {
    const selectedPackages = packages.filter(pkg => pkg.selected);
    
    if (selectedPackages.length === 0) {
      setError('Selecione pelo menos um package');
      return;
    }
    
    setProcessing(true);
    setError('');
    
    try {
      const municResponse = await api.get('/municipalities/?state=CE');
      const fortaleza = municResponse.data.find((m: any) => m.name === 'Fortaleza');
      
      if (!fortaleza) {
        throw new Error('Município Fortaleza não encontrado');
      }
      
      const response = await api.post('/portal/ingest/start', {
        packages: selectedPackages.map(p => p.name),
        municipality_id: fortaleza.id
      });
      
      console.log('[INGEST] Response completo:', response.data);
      
      if (!response.data.job_id) {
        throw new Error('Job ID não retornado pelo servidor');
      }
      
      const newJob = {
        job_id: response.data.job_id,
        status: response.data.status || 'processing',
        total_packages: selectedPackages.length,
        processed_packages: 0,
        failed_packages: 0,
        total_documents: 0
      };
      
      setCurrentJob(newJob);
      
      console.log('[INGEST] Job iniciado:', newJob.job_id);
      console.log('[INGEST] Job object:', newJob);
    } catch (err: any) {
      console.error('Erro ao iniciar processamento:', err);
      setError(err.response?.data?.detail || 'Erro ao iniciar processamento');
      setProcessing(false);
    }
  };
  
  const deleteCollection = async (collectionName: string) => {
    if (!confirm(`Deletar collection "${collectionName}"?`)) {
      return;
    }
    
    try {
      await api.delete(`/portal/ingest/collection/${collectionName}`);
      loadCollections();
      console.log('[INGEST] Collection deletada:', collectionName);
    } catch (err) {
      console.error('Erro ao deletar collection:', err);
      setError('Erro ao deletar collection');
    }
  };
  
  const cancelJob = async () => {
    if (!currentJob) return;
    
    if (!confirm('Cancelar o processamento atual?')) {
      return;
    }
    
    try {
      await api.post(`/portal/ingest/cancel-job/${currentJob.job_id}`);
      setCurrentJob(null);
      setProcessing(false);
      setProgress(null);
      loadCollections();
      loadProcessedPackages();
      console.log('[INGEST] Job cancelado');
    } catch (err) {
      console.error('Erro ao cancelar job:', err);
      setError('Erro ao cancelar job');
    }
  };
  
  const filteredPackages = getFilteredPackages();
  const selectedCount = packages.filter(p => p.selected).length;
  const allFilteredSelected = filteredPackages.length > 0 && filteredPackages.every(p => p.selected);
  
  return (
    <div className="bg-gray-50 py-8">
      <div className="container mx-auto px-4 max-w-7xl">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Ingestão do Portal da Transparência
          </h1>
          <p className="text-gray-600">
            Selecione e processe packages do Portal para armazenar no ChromaDB
          </p>
        </div>
        
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4 flex items-start">
            <AlertCircle className="w-5 h-5 text-red-500 mr-3 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-medium text-red-900">Erro</h3>
              <p className="text-red-700 text-sm">{error}</p>
            </div>
          </div>
        )}
        
        {currentJob && (
          <div className="mb-6 bg-blue-50 border border-blue-200 rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-blue-900">
                Processamento em Andamento
              </h3>
              <div className="flex items-center gap-3">
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                  currentJob.status === 'completed' ? 'bg-green-100 text-green-800' :
                  currentJob.status === 'failed' ? 'bg-red-100 text-red-800' :
                  'bg-blue-100 text-blue-800'
                }`}>
                  {currentJob.status}
                </span>
                {(currentJob.status === 'processing' || currentJob.status === 'pending') && (
                  <button
                    onClick={cancelJob}
                    className="flex items-center gap-1 px-3 py-1 text-sm bg-red-100 hover:bg-red-200 text-red-700 rounded-lg transition-colors"
                    title="Cancelar processamento"
                  >
                    <XCircle className="w-4 h-4" />
                    Cancelar
                  </button>
                )}
              </div>
            </div>
            
            <div className="space-y-3">
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-gray-700">Progresso</span>
                  <span className="font-medium text-gray-900">
                    {currentJob.processed_packages} / {currentJob.total_packages} packages
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div
                    className="bg-blue-600 h-3 rounded-full transition-all duration-300"
                    style={{
                      width: `${(currentJob.processed_packages / currentJob.total_packages) * 100}%`
                    }}
                  />
                </div>
              </div>
              
              {progress && (
                <div className="space-y-2">
                  <p className="text-sm text-gray-600">
                    <span className="font-medium">{progress.message}</span>
                  </p>
                  
                  {/* Progresso de batches (quando disponível) */}
                  {progress.current_batch !== undefined && progress.total_batches !== undefined && (
                    <div>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-gray-600">Batches de embeddings</span>
                        <span className="font-medium text-gray-900">
                          {progress.current_batch}/{progress.total_batches}
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-green-600 h-2 rounded-full transition-all duration-300"
                          style={{
                            width: `${progress.percentage}%`
                          }}
                        />
                      </div>
                    </div>
                  )}
                  
                  {/* Progresso de packages (quando não há info de batches) */}
                  {progress.current_package_index !== undefined && progress.total_packages !== undefined && !progress.current_batch && (
                    <div className="flex items-center gap-2 text-xs text-gray-500">
                      <span>Package {progress.current_package_index} de {progress.total_packages}</span>
                      <span>•</span>
                      <span>{progress.percentage}%</span>
                    </div>
                  )}
                  
                  {progress.documents_inserted > 0 && (
                    <div className="text-xs text-gray-500">
                      <span className="font-medium">{progress.documents_inserted.toLocaleString()}</span> documentos processados
                    </div>
                  )}
                </div>
              )}
              
              {!progress && currentJob.current_package && (
                <p className="text-sm text-gray-600">
                  Processando: <span className="font-medium">{currentJob.current_package}</span>
                </p>
              )}
              
              <div className="flex gap-4 text-sm">
                <span className="text-gray-600">
                  Documentos inseridos: <span className="font-medium text-gray-900">
                    {currentJob.total_documents.toLocaleString()}
                  </span>
                </span>
                {currentJob.failed_packages > 0 && (
                  <span className="text-red-600">
                    Falhas: <span className="font-medium">{currentJob.failed_packages}</span>
                  </span>
                )}
              </div>
            </div>
          </div>
        )}
        
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200">
              <div className="p-4 border-b border-gray-200">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-semibold text-gray-900">
                    Packages Disponíveis ({filteredPackages.length})
                  </h2>
                  <button
                    onClick={loadPackages}
                    disabled={loading}
                    className="flex items-center gap-2 px-3 py-2 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors disabled:opacity-50"
                  >
                    <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                    Atualizar
                  </button>
                </div>
                
                <div className="relative mb-4">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                  <input
                    type="text"
                    placeholder="Buscar packages..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
                
                <div className="flex items-center justify-between">
                  <button
                    onClick={selectAll}
                    className="flex items-center gap-2 text-sm text-blue-600 hover:text-blue-700 font-medium"
                  >
                    {allFilteredSelected ? (
                      <>
                        <CheckSquare className="w-4 h-4" />
                        Desmarcar Todos
                      </>
                    ) : (
                      <>
                        <Square className="w-4 h-4" />
                        Selecionar Todos
                      </>
                    )}
                  </button>
                  <span className="text-sm text-gray-600">
                    {selectedCount} selecionados
                  </span>
                </div>
              </div>
              
              <div className="divide-y divide-gray-200 max-h-[600px] overflow-y-auto">
                {loading ? (
                  <div className="p-8 text-center">
                    <RefreshCw className="w-8 h-8 animate-spin mx-auto text-gray-400 mb-2" />
                    <p className="text-gray-500">Carregando packages...</p>
                  </div>
                ) : filteredPackages.length === 0 ? (
                  <div className="p-8 text-center text-gray-500">
                    Nenhum package encontrado
                  </div>
                ) : (
                  filteredPackages.map((pkg) => (
                    <label
                      key={pkg.name}
                      className={`flex items-center p-4 hover:bg-gray-50 cursor-pointer transition-colors ${
                        pkg.processed ? 'bg-green-50/30' : ''
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={pkg.selected}
                        onChange={() => togglePackage(pkg.name)}
                        className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                      />
                      <div className="ml-3 flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <p className="font-medium text-gray-900">{pkg.name}</p>
                          {pkg.processed && (
                            <div className="flex items-center gap-2">
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                <CheckCircle className="w-3 h-3" />
                                Processado
                              </span>
                              {pkg.total_documents !== undefined && pkg.total_documents > 0 && (
                                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                  {pkg.total_documents.toLocaleString()} documentos
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                        {pkg.processed && pkg.last_processed && (
                          <div className="mt-1 text-xs text-gray-500">
                            Último processamento: {new Date(pkg.last_processed).toLocaleString('pt-BR')}
                          </div>
                        )}
                      </div>
                    </label>
                  ))
                )}
              </div>
              
              <div className="p-4 border-t border-gray-200 bg-gray-50">
                <button
                  onClick={startProcessing}
                  disabled={selectedCount === 0 || processing}
                  className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                >
                  <Play className="w-5 h-5" />
                  {processing ? 'Processando...' : `Processar ${selectedCount} Packages`}
                </button>
              </div>
            </div>
          </div>
          
          <div>
            <div className="bg-white rounded-lg shadow-sm border border-gray-200">
              <div className="p-4 border-b border-gray-200">
                <h2 className="text-lg font-semibold text-gray-900">
                  Collections ({collections.length})
                </h2>
                <p className="text-sm text-gray-500 mt-1">
                  Packages já processados
                </p>
              </div>
              
              <div className="divide-y divide-gray-200 max-h-[600px] overflow-y-auto">
                {collections.length === 0 ? (
                  <div className="p-8 text-center text-gray-500 text-sm">
                    Nenhuma collection processada ainda
                  </div>
                ) : (
                  collections.map((collection) => (
                    <div
                      key={collection}
                      className="flex items-center justify-between p-4 hover:bg-gray-50"
                    >
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-gray-900 text-sm truncate">
                          {collection.replace('portal_', '')}
                        </p>
                      </div>
                      <button
                        onClick={() => deleteCollection(collection)}
                        className="ml-2 p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                        title="Deletar collection"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

