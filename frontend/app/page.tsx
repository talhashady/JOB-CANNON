import Background from "@/components/Background";
import Navbar from "@/components/Navbar";
import Hero from "@/components/Hero";
import HowItWorks from "@/components/HowItWorks";
import AgentsShowcase from "@/components/AgentsShowcase";
import PipelineRunner from "@/components/PipelineRunner";
import Footer from "@/components/Footer";

export default function Home() {
  return (
    <main className="relative">
      <Background />
      <Navbar />
      <Hero />
      <HowItWorks />
      <AgentsShowcase />
      <PipelineRunner />
      <Footer />
    </main>
  );
}
