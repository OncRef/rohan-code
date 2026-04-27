'use client'

import React, { useState, useEffect } from 'react'

export default function MoaStats() {
  const [drugs, setDrugs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [sortBy, setSortBy] = useState('generic_name')
  const [sortOrder, setSortOrder] = useState('asc')
  const [filterMoaStatus, setFilterMoaStatus] = useState('all') // 'all', 'missing', 'empty', 'filled'

  useEffect(() => {
    fetchDrugsWithMoa()
  }, [])

  const fetchDrugsWithMoa = async () => {
    try {
      setLoading(true)
      const response = await fetch('/api/pr-trigger/fix_moa/stats')
      const data = await response.json()
      
      if (!response.ok) throw new Error(data.error || 'Failed to fetch data')
      
      setDrugs(data.drugs)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // Filter and sort drugs
  const filteredDrugs = drugs
    .filter(drug => {
      // First apply MOA status filter
      if (filterMoaStatus === 'missing') {
        if (drug.short_moa !== undefined) return false
      } else if (filterMoaStatus === 'empty') {
        if (!drug.short_moa || drug.short_moa.trim() === 'None') return true
        return false
      } else if (filterMoaStatus === 'filled') {
        if (!drug.short_moa || drug.short_moa.trim() === '') return false
      }

      // Then apply search term filter
      return (
        drug.generic_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        drug.brand_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        drug._id?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        drug.short_moa?.toLowerCase().includes(searchTerm.toLowerCase())
      )
    })
    .sort((a, b) => {
      let valueA = a[sortBy]
      let valueB = b[sortBy]
      
      // Special handling for dates
      if (sortBy === 'short_moa_updated_at') {
        valueA = valueA ? new Date(valueA).getTime() : 0
        valueB = valueB ? new Date(valueB).getTime() : 0
      }
      
      // Handle null/undefined values
      if (valueA === null || valueA === undefined) return sortOrder === 'asc' ? -1 : 1
      if (valueB === null || valueB === undefined) return sortOrder === 'asc' ? 1 : -1
      
      // Normal string/number comparison
      if (valueA < valueB) return sortOrder === 'asc' ? -1 : 1
      if (valueA > valueB) return sortOrder === 'asc' ? 1 : -1
      return 0
    })

  return (
    <div className="min-h-screen bg-gray-100 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-4">MOA Statistics</h1>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <div className="text-sm text-gray-500">
                Showing {filteredDrugs.length} of {drugs.length} drugs
              </div>
              <input
                type="text"
                placeholder="Search by name, SetID, or MOA..."
                className="w-1/3 p-2 border rounded"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            
            <div className="flex space-x-4 items-center">
              <div className="flex items-center space-x-2">
                <label className="text-sm text-gray-600">Filter by MOA Status:</label>
                <select
                  className="p-2 border rounded bg-white"
                  value={filterMoaStatus}
                  onChange={(e) => setFilterMoaStatus(e.target.value)}
                >
                  <option value="all">All Drugs</option>
                  <option value="missing">Missing MOA Field</option>
                  <option value="empty">Empty MOA</option>
                  <option value="filled">Has MOA</option>
                </select>
              </div>

              <div className="flex items-center space-x-2">
                <label className="text-sm text-gray-600">Sort by:</label>
                <select
                  className="p-2 border rounded bg-white"
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                >
                  <option value="generic_name">Generic Name</option>
                  <option value="brand_name">Brand Name</option>
                  <option value="short_moa_updated_at">Last Updated</option>
                  <option value="_id">SetID</option>
                </select>
              </div>

              <button
                className="p-2 text-sm text-blue-600 hover:text-blue-800"
                onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
              >
                {sortOrder === 'asc' ? '↑ Ascending' : '↓ Descending'}
              </button>
            </div>
          </div>
        </div>

        {loading ? (
          <div className="text-center py-4">Loading...</div>
        ) : error ? (
          <div className="bg-red-100 text-red-700 p-4 rounded">
            Error: {error}
          </div>
        ) : (
          <div className="bg-white shadow-md rounded-lg overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th
                      onClick={() => setSortBy('_id')}
                      className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                    >
                      SetID {sortBy === '_id' && (sortOrder === 'asc' ? ' ↑' : ' ↓')}
                    </th>
                    <th
                      onClick={() => setSortBy('generic_name')}
                      className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                    >
                      Generic Name {sortBy === 'generic_name' && (sortOrder === 'asc' ? ' ↑' : ' ↓')}
                    </th>
                    <th
                      onClick={() => setSortBy('brand_name')}
                      className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                    >
                      Brand Name {sortBy === 'brand_name' && (sortOrder === 'asc' ? ' ↑' : ' ↓')}
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Short MOA
                    </th>
                    <th
                      onClick={() => setSortBy('short_moa_updated_at')}
                      className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                    >
                      Last Updated {sortBy === 'short_moa_updated_at' && (sortOrder === 'asc' ? ' ↑' : ' ↓')}
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {filteredDrugs.map((drug, idx) => (
                    <tr key={drug._id} className={idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-mono">
                        {drug._id}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        {drug.generic_name}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        {drug.brand_name}
                      </td>
                      <td className="px-6 py-4 text-sm">
                        {drug.short_moa}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {drug.short_moa_updated_at ? new Date(drug.short_moa_updated_at).toLocaleDateString() : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}