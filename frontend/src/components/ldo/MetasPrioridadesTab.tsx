import { useState, useEffect } from 'react';
import { ldoApi, type MetasPrioridadesData } from '../../services/api';
import { Target, TrendingUp, Flag, Calendar, AlertCircle } from 'lucide-react';

interface MetasPrioridadesTabProps {
  ano: number | null;
}

export default function MetasPrioridadesTab({ ano }: MetasPrioridadesTabProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<MetasPrioridadesData | null>(null);

  useEffect(() => {
    if (ano) {
      loadData();
    }
  }, [ano]);

  const loadData = async () => {
    if (!ano) return;

    try {
      setLoading(true);
      setError(null);
      const result = await ldoApi.getMetasPrioridades(ano);
      setData(result);
    } catch (err) {
      console.error('Erro ao carregar metas e prioridades:', err);
      setError('Erro ao carregar dados. Verifique se a LDO foi processada.');
    } finally {
      setLoading(false);
    }
  };

  if (!ano) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">Selecione um ano para visualizar as metas e prioridades</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
        <AlertCircle className="w-12 h-12 text-red-600 mx-auto mb-3" />
        <p className="text-red-800 font-medium">{error}</p>
      </div>
    );
  }

  if (!data || (!data.prioridades?.length && !data.diretrizes_gerais?.length)) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
        <AlertCircle className="w-12 h-12 text-yellow-600 mx-auto mb-3" />
        <p className="text-yellow-800">Nenhuma meta ou prioridade encontrada para este ano.</p>
      </div>
    );
  }

  const setorColors: Record<string, string> = {
    'Educação': 'bg-blue-100 text-blue-800 border-blue-300',
    'Saúde': 'bg-green-100 text-green-800 border-green-300',
    'Segurança': 'bg-red-100 text-red-800 border-red-300',
    'Infraestrutura': 'bg-orange-100 text-orange-800 border-orange-300',
    'Assistência Social': 'bg-purple-100 text-purple-800 border-purple-300',
    'Mobilidade': 'bg-cyan-100 text-cyan-800 border-cyan-300',
    'Meio Ambiente': 'bg-emerald-100 text-emerald-800 border-emerald-300',
    'Cultura': 'bg-pink-100 text-pink-800 border-pink-300',
    'Esporte': 'bg-indigo-100 text-indigo-800 border-indigo-300',
  };

  const getSetorColor = (setor: string) => {
    return setorColors[setor] || 'bg-gray-100 text-gray-800 border-gray-300';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg p-6">
        <h2 className="text-2xl font-bold mb-2">Metas e Prioridades {ano}</h2>
        <p className="text-blue-100">
          Diretrizes estratégicas e prioridades governamentais definidas na LDO
        </p>
        {data.prefeito && (
          <p className="text-sm text-blue-100 mt-2">
            Gestão: {data.prefeito}
          </p>
        )}
      </div>

      {/* Prioridades Governamentais */}
      {data.prioridades && data.prioridades.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center gap-3 mb-6">
            <Flag className="w-6 h-6 text-blue-600" />
            <h3 className="text-xl font-bold text-gray-900">Prioridades Governamentais</h3>
          </div>

          <div className="space-y-4">
            {data.prioridades.map((prioridade, idx) => (
              <div
                key={idx}
                className={`border-l-4 ${
                  prioridade.ordem <= 3 ? 'border-blue-600' : 'border-gray-300'
                } pl-4 py-2`}
              >
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0">
                    <div
                      className={`w-8 h-8 rounded-full flex items-center justify-center font-bold ${
                        prioridade.ordem <= 3
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-200 text-gray-600'
                      }`}
                    >
                      {prioridade.ordem}
                    </div>
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span
                        className={`px-3 py-1 rounded-full text-xs font-semibold border ${getSetorColor(
                          prioridade.setor
                        )}`}
                      >
                        {prioridade.setor}
                      </span>
                    </div>
                    <h4 className="font-semibold text-gray-900 mb-1">{prioridade.titulo}</h4>
                    {prioridade.descricao && (
                      <p className="text-sm text-gray-600 mb-2">{prioridade.descricao}</p>
                    )}
                    {prioridade.meta_quantitativa && (
                      <div className="flex items-center gap-2 text-sm text-blue-600 mb-1">
                        <Target className="w-4 h-4" />
                        <span className="font-medium">Meta: {prioridade.meta_quantitativa}</span>
                      </div>
                    )}
                    {prioridade.prazo && (
                      <div className="flex items-center gap-2 text-sm text-gray-500">
                        <Calendar className="w-4 h-4" />
                        <span>Prazo: {prioridade.prazo}</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Diretrizes Gerais */}
      {data.diretrizes_gerais && data.diretrizes_gerais.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center gap-3 mb-4">
            <TrendingUp className="w-6 h-6 text-green-600" />
            <h3 className="text-xl font-bold text-gray-900">Diretrizes Gerais</h3>
          </div>

          <ul className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {data.diretrizes_gerais.map((diretriz, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <div className="flex-shrink-0 w-2 h-2 bg-green-600 rounded-full mt-2"></div>
                <span className="text-gray-700">{diretriz}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Metas Setoriais */}
      {data.metas_setoriais && Object.keys(data.metas_setoriais).length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-xl font-bold text-gray-900 mb-4">Metas Setoriais</h3>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Object.entries(data.metas_setoriais).map(([setor, meta]) => (
              <div key={setor} className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                <div className={`inline-block px-3 py-1 rounded-full text-sm font-semibold mb-3 ${getSetorColor(setor)}`}>
                  {setor.charAt(0).toUpperCase() + setor.slice(1)}
                </div>

                <h4 className="font-semibold text-gray-900 mb-2">{meta.meta}</h4>
                
                {meta.indicador && (
                  <p className="text-sm text-gray-600 mb-3">
                    <strong>Indicador:</strong> {meta.indicador}
                  </p>
                )}

                <div className="flex items-center justify-between text-sm mb-2">
                  <span className="text-gray-600">Atual:</span>
                  <span className="font-semibold text-gray-900">
                    {meta.valor_atual} {meta.unidade}
                  </span>
                </div>

                <div className="flex items-center justify-between text-sm mb-3">
                  <span className="text-gray-600">Meta:</span>
                  <span className="font-semibold text-blue-600">
                    {meta.valor_meta} {meta.unidade}
                  </span>
                </div>

                {meta.recursos_necessarios && (
                  <div className="pt-3 border-t border-gray-100">
                    <p className="text-xs text-gray-500">
                      Recursos: R$ {(meta.recursos_necessarios / 1000000).toFixed(1)}M
                    </p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Programas Prioritários */}
      {data.programas_prioritarios && data.programas_prioritarios.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-xl font-bold text-gray-900 mb-4">Programas Prioritários</h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {data.programas_prioritarios.map((programa, idx) => (
              <div key={idx} className="border border-gray-200 rounded-lg p-4">
                {programa.codigo && (
                  <span className="text-xs font-mono text-gray-500">Código {programa.codigo}</span>
                )}
                <h4 className="font-semibold text-gray-900 mt-1">{programa.nome}</h4>
                {programa.justificativa && (
                  <p className="text-sm text-gray-600 mt-2">{programa.justificativa}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Diretrizes Setoriais */}
      {data.diretrizes_setoriais && Object.keys(data.diretrizes_setoriais).length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-xl font-bold text-gray-900 mb-4">Diretrizes Setoriais</h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {Object.entries(data.diretrizes_setoriais).map(([setor, diretrizes]) => (
              <div key={setor}>
                <h4 className={`font-semibold mb-2 px-3 py-1 rounded inline-block ${getSetorColor(setor)}`}>
                  {setor.charAt(0).toUpperCase() + setor.slice(1)}
                </h4>
                <ul className="mt-3 space-y-2">
                  {diretrizes.map((diretriz, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-sm">
                      <div className="flex-shrink-0 w-1.5 h-1.5 bg-gray-400 rounded-full mt-1.5"></div>
                      <span className="text-gray-700">{diretriz}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

