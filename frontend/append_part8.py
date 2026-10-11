path = 'c:/Users/LOQ/Downloads/Python_programs/agentic-monetary-policy-india/frontend/components/RecentMacroSignals.tsx'

with open(path, 'a') as f:
    f.write('      {/* Section 3: Economic Watchlist */}\n')
    f.write('      <div className="relative mt-6 border-t border-slate-200/40 pt-5">\n')
    f.write('        <h3 className="text-xs font-semibold text-slate-700 mb-3">Economic Watchlist</h3>\n')
    f.write('        <div className="space-y-2">\n')
    f.write('          {watchlistItems.map((item) => (\n')
    f.write('            <div key={item.key} className="flex items-center gap-3">\n')
    f.write('              <span className={`h-2 w-2 shrink-0 rounded-full ${item.dot}`} />\n')
    f.write('              <span className="flex-1 text-[10px] font-medium text-slate-700">{item.label}</span>\n')
    f.write('              <span className={`text-[9px] font-medium ${item.color} px-1.5 py-0.5 rounded`}>{item.status}</span>\n')
    f.write('              <span className="text-[9px] text-slate-400">{item.detail}</span>\n')
    f.write('            </div>\n')
    f.write('          ))}\n')
    f.write('        </div>\n')
    f.write('      </div>\n\n')
print('Part 8 done')