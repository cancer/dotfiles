require 'rake'

def here(*paths)
  File.expand_path(File.join(File.dirname(__FILE__), *paths))
end

# TODO:dotfilesの取り方探してくる
def dotfiles
  Dir[here('*')].map do |path|
    File.basename(path)
  end.reject do |path|
  end
end

task :default => [:dotfiles]

desc "Symlinks all dotfiles"
task :dotfiles do
  dotfiles.each do |dotfile|
    link = File.expand_path("~/.#{dotfile}")
    sh %Q{echo #{dotfile}}
  end
#  sh %Q{ls -la "#{here('*')}"}
end
