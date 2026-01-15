import ReactMarkdown from 'react-markdown';
import { AlertCircle, CheckCircle, Info, AlertTriangle } from 'lucide-react';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import type { Component } from '../types';

interface ComponentRendererProps {
  component: Component;
}

export default function ComponentRenderer({ component }: ComponentRendererProps) {
  switch (component.type) {
    case 'text':
      return (
        <div className="prose prose-sm max-w-none">
          <ReactMarkdown>{component.content}</ReactMarkdown>
        </div>
      );

    case 'metric':
      return (
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-sm text-gray-600">{component.label}</div>
          <div className="text-2xl font-bold text-gray-900 mt-1">
            {component.value}
          </div>
          {component.change && (
            <div className={`text-sm mt-1 ${
              component.trend === 'up' ? 'text-green-600' :
              component.trend === 'down' ? 'text-red-600' :
              'text-gray-600'
            }`}>
              {component.change}
            </div>
          )}
        </div>
      );

    case 'table':
      return (
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
            <h3 className="text-sm font-medium text-gray-900">{component.title}</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  {component.columns.map((col, idx) => (
                    <th key={idx} className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {component.rows.map((row, ridx) => (
                  <tr key={ridx}>
                    {row.map((cell, cidx) => (
                      <td key={cidx} className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {cell}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      );

    case 'alert':
      const alertStyles = {
        info: { bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-800', Icon: Info },
        warning: { bg: 'bg-yellow-50', border: 'border-yellow-200', text: 'text-yellow-800', Icon: AlertTriangle },
        error: { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-800', Icon: AlertCircle },
        success: { bg: 'bg-green-50', border: 'border-green-200', text: 'text-green-800', Icon: CheckCircle },
      };
      const style = alertStyles[component.level];
      const Icon = style.Icon;
      
      return (
        <div className={`${style.bg} border ${style.border} rounded-lg p-4 flex items-start`}>
          <Icon className={`h-5 w-5 ${style.text} mr-3 mt-0.5 flex-shrink-0`} />
          <div className={`${style.text} text-sm`}>{component.message}</div>
        </div>
      );

    case 'comparison':
      return (
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-900 mb-4">{component.title}</h3>
          <div className="space-y-3">
            {component.items.map((item, idx) => (
              <div key={idx}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-700">{item.label}</span>
                  <span className="font-medium text-gray-900">{item.value}</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-primary-600 h-2 rounded-full"
                    style={{ width: `${item.percentage}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      );

    case 'timeline':
      return (
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-900 mb-4">{component.title}</h3>
          <div className="space-y-4">
            {component.events.map((event, idx) => (
              <div key={idx} className="flex">
                <div className="flex-shrink-0 w-24 text-sm text-gray-500">{event.date}</div>
                <div className="flex-1 ml-4">
                  <div className="font-medium text-gray-900">{event.title}</div>
                  {event.description && (
                    <div className="text-sm text-gray-600 mt-1">{event.description}</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      );

    case 'chart':
      const COLORS = ['#2563eb', '#7c3aed', '#db2777', '#ea580c', '#16a34a', '#0891b2', '#ca8a04', '#dc2626'];
      
      const renderChart = () => {
        if (component.chart_type === 'bar') {
          return (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={component.data}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey={component.x_key} />
                <YAxis />
                <Tooltip />
                <Legend />
                {component.y_keys?.map((key, idx) => (
                  <Bar key={key} dataKey={key} fill={COLORS[idx % COLORS.length]} />
                ))}
              </BarChart>
            </ResponsiveContainer>
          );
        }
        
        if (component.chart_type === 'line') {
          return (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={component.data}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey={component.x_key} />
                <YAxis />
                <Tooltip />
                <Legend />
                {component.y_keys?.map((key, idx) => (
                  <Line key={key} type="monotone" dataKey={key} stroke={COLORS[idx % COLORS.length]} />
                ))}
              </LineChart>
            </ResponsiveContainer>
          );
        }
        
        if (component.chart_type === 'pie') {
          return (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={component.data}
                  dataKey={component.value_key || 'value'}
                  nameKey={component.name_key || 'name'}
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  label
                >
                  {component.data.map((_entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          );
        }
        
        return <div>Tipo de gráfico não suportado</div>;
      };
      
      return (
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-900 mb-4">{component.title}</h3>
          {renderChart()}
        </div>
      );

    default:
      return <div>Componente não suportado</div>;
  }
}

