import { useState, useEffect } from 'react';
import { 
  TrendingDown, 
  Target,
  Loader2
} from 'lucide-react';
import { 
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  Cell
} from 'recharts';
import { dashboardApi, type DespesasData } from '../../services/api';

interface Props {
  ano: number;
}

const CATEGORY_COLORS: Record<string, string> = {
  'Pessoal e Encargos': '#EF4444',
  'Outras Despesas Correntes': '#F97316',
  'Investimentos': '#10B981',
  'Inversões Financeiras': '#3B82F6',
  'Amortização da Dívida': '#8B5CF6',
  'Juros e Encargos da Dívida': '#EC4899',
  'Reserva de Contingência': '#6B7280',
};

export default function DespesasTab({ ano }: Props) {
  const [data, setData] = useState<DespesasData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, [ano]);

  const loadData = async () => {
    try {
      setLoading(true);
      const result = await dashboardApi.getDespesas(ano);
      setData(result);
    } catch (err) {
      console.error('Erro ao carregar despesas:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL',
      notation: 'compact',
      maximumFractionDigits: 2,
    }).format(value);
  };

  const formatFullCurrency = (value: number) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL',
    }).format(value);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 text-blue-600 animate-spin" />
      </div>
    );
  }

  if (!data) return null;

  const categoriaData = data.por_categoria.map(c => ({
    name: c.categoria,
    valor: c.valor_total,
    color: CATEGORY_COLORS[c.categoria] || '#6B7280',
  }));

  return (
    <div className="space-y-6">
      {/* Gráficos lado a lado */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Despesas por Categoria */}
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <div className="flex items-center gap-2 mb-1">
            <TrendingDown className="h-5 w-5 text-red-500" />
            <h3 className="text-lg font-semibold text-gray-900">
              Despesas por Categoria
            </h3>
          </div>
          <p className="text-sm text-gray-500 mb-4">Divisão econômica do orçamento municipal</p>
          
          <ResponsiveContainer width="100%" height={300}>
            <BarChart
              layout="vertical"
              data={categoriaData}
              margin={{ left: 20, right: 20 }}
            >
              <XAxis type="number" tickFormatter={(v) => formatCurrency(v)} />
              <YAxis 
                type="category" 
                dataKey="name" 
                width={150}
                tick={{ fontSize: 11 }}
              />
              <Tooltip formatter={(value: number) => formatFullCurrency(value)} />
              <Bar dataKey="valor" radius={[0, 4, 4, 0]}>
                {categoriaData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Proporção por Esfera */}
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <div className="flex items-center gap-2 mb-1">
            <Target className="h-5 w-5 text-blue-500" />
            <h3 className="text-lg font-semibold text-gray-900">
              Proporção por Esfera
            </h3>
          </div>
          <p className="text-sm text-gray-500 mb-4">Divisão entre Fiscal e Seguridade Social</p>
          
          <ResponsiveContainer width="100%" height={300}>
            <BarChart
              data={data.programas.slice(0, 8).map(p => ({
                name: p.codigo,
                fiscal: p.percentual_fiscal || 50,
                seguridade: p.percentual_seguridade || 50,
              }))}
              margin={{ left: 10, right: 10 }}
            >
              <XAxis dataKey="name" />
              <YAxis tickFormatter={(v) => `${v}%`} />
              <Tooltip />
              <Bar dataKey="fiscal" stackId="a" fill="#3B82F6" name="Orçamento Fiscal" />
              <Bar dataKey="seguridade" stackId="a" fill="#10B981" name="Seguridade Social" />
            </BarChart>
          </ResponsiveContainer>
          
          <div className="flex justify-center gap-6 mt-4">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-blue-500 rounded-full" />
              <span className="text-sm text-gray-600">Orçamento Fiscal</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-green-500 rounded-full" />
              <span className="text-sm text-gray-600">Seguridade Social</span>
            </div>
          </div>
        </div>
      </div>

      {/* Detalhamento Estratégico dos Programas */}
      <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
        <div className="flex items-center gap-2 mb-6">
          <Target className="h-5 w-5 text-blue-600" />
          <h3 className="text-lg font-semibold text-gray-900">
            Detalhamento Estratégico dos Programas
          </h3>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {data.programas.map((prog) => {
            const fiscalPercent = prog.percentual_fiscal || 50;
            const seguridadePercent = prog.percentual_seguridade || 50;
            
            return (
              <div 
                key={prog.codigo} 
                className="border border-gray-200 rounded-xl p-5 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between mb-3">
                  <span className="bg-gray-100 text-gray-600 px-2 py-1 rounded text-xs font-medium">
                    COD. {prog.codigo}
                  </span>
                  <span className="text-blue-600 font-bold text-lg">
                    {formatCurrency(prog.valor_total)}
                  </span>
                </div>
                
                <h4 className="font-semibold text-gray-900 mb-2">{prog.nome}</h4>
                
                {prog.objetivo && (
                  <p className="text-sm text-gray-500 mb-4">{prog.objetivo}</p>
                )}
                
                {/* Barra de proporção */}
                <div className="space-y-2">
                  <div className="flex justify-between text-xs text-gray-500">
                    <span>FISCAL</span>
                    <span>SEGURIDADE</span>
                  </div>
                  <div className="h-2 bg-gray-200 rounded-full overflow-hidden flex">
                    <div 
                      className="bg-blue-500 h-full transition-all"
                      style={{ width: `${fiscalPercent}%` }}
                    />
                    <div 
                      className="bg-green-500 h-full transition-all"
                      style={{ width: `${seguridadePercent}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-blue-600 font-medium">{fiscalPercent.toFixed(0)}%</span>
                    <span className="text-green-600 font-medium">{seguridadePercent.toFixed(0)}%</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Consolidado */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-800 rounded-xl p-6 text-white">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-white/20 p-2 rounded-lg">
              <TrendingDown className="h-6 w-6" />
            </div>
            <div>
              <p className="text-blue-100 text-sm">CONSOLIDADO DO EXERCÍCIO</p>
              <p className="text-2xl font-bold">Despesa Total Fixada</p>
            </div>
          </div>
          <p className="text-4xl font-bold">
            {formatCurrency(data.despesa_total)}
          </p>
        </div>
      </div>
    </div>
  );
}

