Extraction Review
=================

.. raw:: html

   <div class="enterprise-workspace-grid dashboard-workspace-grid">
     <div class="enterprise-workspace-center">
       <section class="dashboard-executive-panel dashboard-executive-panel-primary">
         <div class="micro-label">Extraction Quality Gate</div>
         <h2>Candidate Review</h2>
         <p>LEAP scanned the selected workspace and promoted only candidates with sufficient KPI evidence into executive dossiers. Weak or ambiguous candidates remain visible here for source-owner review.</p>
         <div class="dashboard-readiness-row">
           <div class="leap-metric-card metric-indicator-block">
             <span class="metric-indicator-label leap-card-label">Quarantined Candidates</span>
             <span class="metric-indicator-value leap-card-value">2</span>
             <span class="leap-card-caption">not counted as Enterprise KPIs</span>
           </div>
           <div class="leap-metric-card metric-indicator-block">
             <span class="metric-indicator-label leap-card-label">Implementation Files</span>
             <span class="metric-indicator-value leap-card-value">30</span>
             <span class="leap-card-caption">evaluated by extractor</span>
           </div>
         </div>
         <p class="leap-card-caption">Source scanned: data/demo/sample_project</p>
       </section>
       <section class="dashboard-dossier-section">
         <div class="dashboard-section-heading">
           <div>
             <div class="micro-label">Candidate Quarantine</div>
             <h2>Extraction Review Items</h2>
           </div>
         </div>
         <div class="portfolio-dossier-list dashboard-recent-list">
           
           <details class="sidebar-card leap-card-tertiary extraction-review-item">
             <summary>
               <h3>calculate vibration index</h3>
               <span class="sidebar-status-badge state-needs-review"><span class="status-dot"></span>Candidate Only</span>
             </summary>
             <div class="card-row"><span class="label">Detection:</span><span class="value">python_function</span></div>
             <div class="card-row"><span class="label">Language:</span><span class="value">python</span></div>
             <div class="card-row"><span class="label">Source:</span><span class="value code-font">data/demo/sample_project/conflict_threshold_vibration.py</span></div>
             <div class="card-row"><span class="label">Line:</span><span class="value">15</span></div>
             <div class="review-signal-card signal-owner">
               <div class="signal-title">Why it was not promoted</div>
               <div class="signal-message">Inferred Python symbol does not return a local arithmetic KPI calculation.</div>
             </div>
             <div class="review-signal-card signal-technical">
               <div class="signal-title">Recommended action</div>
               <div class="signal-message">Add explicit KPI/Formula metadata or keep this helper function out of governed KPI dossiers.</div>
             </div>
             <pre class="font-mono"># Input: Peak vibration (mm/s), Baseline safe threshold (mm/s)
   # Unit: dimensionless ratio
   # Reporting Source: OSIsoft PI System (Historian)
   # Used In: Reliability Dashboard, Predictive Maintenance Alert System

   # Threshold conflict: A higher Vibration Index means MORE vibration relative to baseline —
   # meaning higher is WORSE (indicates machine degradation approaching failure).
   # However, the logic below treats higher values as BETTER (returns &#x27;GOOD&#x27; for high values),
   # inverting the business interpretation of this KPI.

   def calculate_vibration_index(peak_vibration_mm_s: float, baseline_threshold_mm_s: float) -&gt; float:
       if baseline_threshold_mm_s &lt;= 0:
           return 0.0
       index = peak_vibration_mm_s / baseline_threshold_mm_s

       # CONFLICT: threshold interpretation is inverted.</pre>
           </details>
           

           <details class="sidebar-card leap-card-tertiary extraction-review-item">
             <summary>
               <h3>SOx Emissions Concentration (kg/m3)</h3>
               <span class="sidebar-status-badge state-needs-review"><span class="status-dot"></span>Candidate Only</span>
             </summary>
             <div class="card-row"><span class="label">Detection:</span><span class="value">comment</span></div>
             <div class="card-row"><span class="label">Language:</span><span class="value">iec_st</span></div>
             <div class="card-row"><span class="label">Source:</span><span class="value code-font">data/demo/sample_project/lc_kpi.st</span></div>
             <div class="card-row"><span class="label">Line:</span><span class="value">1</span></div>
             <div class="review-signal-card signal-owner">
               <div class="signal-title">Why it was not promoted</div>
               <div class="signal-message">Explicit KPI marker found, but no formula, executable calculation, or business metadata was found nearby.</div>
             </div>
             <div class="review-signal-card signal-technical">
               <div class="signal-title">Recommended action</div>
               <div class="signal-message">Add Formula, Objective, Unit, Owner, or executable calculation evidence.</div>
             </div>
             <pre class="font-mono">// KPI: SOx Emissions Concentration (kg/m3)
   VAR
       soxConc : REAL := 0.0;
       soxMassFlow : REAL := 0.0;
       volFlow : REAL := 0.0;
   END_VAR

   (* Example structured text placeholder *)
   soxConc := 15.2; (* pretend this comes from an analyzer tag *)
   soxMassFlow := 233.4;
   volFlow := 15.3;</pre>
           </details>
           
           
         </div>
       </section>
     </div>
   </div>
