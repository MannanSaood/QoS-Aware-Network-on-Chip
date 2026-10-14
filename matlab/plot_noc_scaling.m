function plot_noc_scaling(resultDir)
% PLOT_NOC_SCALING Line-only p50/p90/p99, throughput and congestion vs mesh size.
if nargin<1, resultDir=fullfile('results','scaling'); end
T=readtable(fullfile(resultDir,'metrics.csv'),'TextType','string');
T=T(T.status=="ok",:); assert(~isempty(T),'No successful rows.');
outputDir=fullfile(resultDir,'matlab_figures');
if ~isfolder(outputDir), mkdir(outputDir); end
save(fullfile(outputDir,'simulation_data.mat'),'T');
algorithms=["xy","dyad","topsis"];
engines=["booksim","ns2"];
metrics=["latency_p50_cycles","latency_p90_cycles","latency_p99_cycles", ...
    "throughput_flits_per_node_cycle","congested_port_time_pct"];
labels=["p50 latency (cycles)","p90 latency (cycles)","p99 latency (cycles)", ...
    "Throughput (flits/node/cycle)","Congested port-time (%)"];
colors=[0 .447 .698; .835 .369 0; 0 .620 .451];
styles={'-','--','-.'};
for traffic=reshape(unique(T.traffic),1,[])
    for offered=reshape(unique(T.offered_flits_per_node_cycle),1,[])
        G=T(T.traffic==traffic & T.offered_flits_per_node_cycle==offered,:);
        f=figure('Visible','off','Color','w','Units','centimeters','Position',[1 1 45 20]);
        if isprop(f,'Theme'), f.Theme='light'; end
        tiles=tiledlayout(f,2,5,'TileSpacing','compact','Padding','compact');
        for ei=1:2
            for mi=1:5
                ax=nexttile(tiles); hold(ax,'on');
                for ai=1:3
                    A=G(G.simulator==engines(ei) & G.algorithm==algorithms(ai),:);
                    sides=unique(A.mesh_k); mu=nan(size(sides)); ci=zeros(size(sides));
                    for si=1:numel(sides)
                        values=A.(metrics(mi))(A.mesh_k==sides(si)); values=values(isfinite(values));
                        n=numel(values); if n==0, continue; end
                        mu(si)=mean(values);
                        if n>1
                            df=n-1; z=betaincinv(.05,df/2,.5);
                            ci(si)=sqrt(df*(1-z)/z)*std(values)/sqrt(n);
                        end
                    end
                    lower=mu-ci; if mi<=3, lower=max(lower,.1); end
                    fill(ax,[sides;flipud(sides)],[lower;flipud(mu+ci)],colors(ai,:), ...
                        'FaceAlpha',.12,'EdgeColor','none','HandleVisibility','off');
                    plot(ax,sides,mu,'LineStyle',styles{ai},'Color',colors(ai,:), ...
                        'LineWidth',1.8,'DisplayName',upper(algorithms(ai)));
                end
                set(ax,'XScale','log','XTick',[4 8 16 32],'XTickLabel',{'4x4','8x8','16x16','32x32'}, ...
                    'FontName','Arial','FontSize',9,'Box','off','TickDir','out','GridAlpha',.15);
                set(ax,'Color','w','XColor',[.15 .15 .15],'YColor',[.15 .15 .15],'GridColor',[.3 .3 .3]);
                xlabel(ax,'Mesh size'); ylabel(ax,labels(mi)); grid(ax,'on');
                if mi<=3, set(ax,'YScale','log'); else, ylim(ax,[0 Inf]); end
                if mi==1
                    title(ax,upper(engines(ei)),'FontSize',12,'Color',[.1 .1 .1]);
                    legend(ax,'Location','best','Box','off','TextColor',[.1 .1 .1],'Color','w');
                end
            end
        end
        title(tiles,sprintf('Mesh scaling | %s | offered load %.3g flits/node/cycle',traffic,offered),'FontSize',15,'Color',[.1 .1 .1]);
        subtitle(tiles,'Lines: seed means; bands: 95% t-intervals. Arrival-conditioned latency; read alongside throughput.','FontSize',10,'Color',[.25 .25 .25]);
        stem=sprintf('scaling_%s_load%g',traffic,offered);
        exportgraphics(f,fullfile(outputDir,stem+".pdf"),'ContentType','vector');
        exportgraphics(f,fullfile(outputDir,stem+".png"),'Resolution',600);
        savefig(f,fullfile(outputDir,stem+".fig")); close(f);
    end
end
fprintf('MATLAB scaling figures: %s\n',outputDir);
end
